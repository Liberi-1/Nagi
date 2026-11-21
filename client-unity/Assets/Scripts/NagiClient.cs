using System;
using System.Collections;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public class NagiClient : MonoBehaviour
{
    [Header("把角色的 Animator 拖进来")]
    public Animator animator;
    [Header("把 AudioSource 拖进来")]
    public AudioSource audioSource;

    private ClientWebSocket ws;
    private AudioClip recording;
    private bool isRecording;
    private bool isBusy;                 // 等待回复/播放中时，屏蔽新的录音
    private const int SampleRate = 16000;

    [Serializable]
    public class ResponseHeader
    {
        public string type;
        public string request_id;
        public string text;
        public string emotion;
        public string audio_format;
        public string code;
        public string message;
    }

    async void Start()
    {
        ws = new ClientWebSocket();
        try
        {
            await ws.ConnectAsync(new Uri("ws://localhost:8765"), CancellationToken.None);
            Debug.Log("已连接 Nagi 服务，按 R 开始说话");
        }
        catch (Exception e)
        {
            Debug.LogError($"连接失败：{e.Message}");
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.R) && !isBusy)
        {
            if (!isRecording) StartRecording();
            else StopAndSend();
        }
    }

    void StartRecording()
    {
        recording = Microphone.Start(Microphone.devices[0], false, 10, SampleRate);
        isRecording = true;
        Debug.Log("录音中……再按 R 停止并发送");
    }

    async void StopAndSend()
    {
        Microphone.End(Microphone.devices[0]);
        isRecording = false;
        isBusy = true;

        try
        {
            byte[] wavBytes = ToWavBytes(recording);
            string requestId = Guid.NewGuid().ToString("N").Substring(0, 8);
            string json = "{\"type\":\"chat_request\",\"request_id\":\"" + requestId
                        + "\",\"audio_format\":\"wav\",\"sample_rate\":" + recording.frequency + "}";

            await ws.SendAsync(PackFrame(json, wavBytes), WebSocketMessageType.Binary,
                               true, CancellationToken.None);
            Debug.Log("录音已上传，等待 Nagi 回复……");

            HandleResponse(await ReceiveFullMessage());
        }
        catch (Exception e)
        {
            Debug.LogError($"通信出错：{e.Message}");
            isBusy = false;
        }
    }

    void HandleResponse(byte[] frame)
    {
        // 解包：4 字节大端头长度 + JSON 头 + 音频负载
        int n = (frame[0] << 24) | (frame[1] << 16) | (frame[2] << 8) | frame[3];
        string json = Encoding.UTF8.GetString(frame, 4, n);
        var header = JsonUtility.FromJson<ResponseHeader>(json);

        if (header.type == "error")
        {
            Debug.LogError($"服务端错误 {header.code}：{header.message}");
            isBusy = false;
            return;
        }

        Debug.Log($"Nagi：{header.text}（情绪：{header.emotion}）");

        byte[] mp3 = new byte[frame.Length - 4 - n];
        Array.Copy(frame, 4 + n, mp3, 0, mp3.Length);

        string path = Path.Combine(Application.persistentDataPath, "reply.mp3");
        File.WriteAllBytes(path, mp3);
        StartCoroutine(PlayReply(path));
    }

    IEnumerator PlayReply(string path)
    {
        using var request = UnityWebRequestMultimedia.GetAudioClip("file://" + path, AudioType.MPEG);
        yield return request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"音频加载失败：{request.error}");
            isBusy = false;
            yield break;
        }

        audioSource.clip = DownloadHandlerAudioClip.GetContent(request);
        audioSource.Play();
        animator.SetBool("IsTalking", true);          // 开始说话：切 Talking

        while (audioSource.isPlaying)
            yield return null;

        animator.SetBool("IsTalking", false);         // 播放结束：回 Idle
        isBusy = false;
        Debug.Log("播放结束，回到 Idle，可以再按 R 说话");
    }

    async Task<byte[]> ReceiveFullMessage()
    {
        // WebSocket 可能分段返回，必须收到 EndOfMessage 才算完整
        var ms = new MemoryStream();
        var buffer = new byte[8192];
        while (true)
        {
            var result = await ws.ReceiveAsync(buffer, CancellationToken.None);
            ms.Write(buffer, 0, result.Count);
            if (result.EndOfMessage) break;
        }
        return ms.ToArray();
    }

    static byte[] PackFrame(string json, byte[] payload)
    {
        byte[] headerBytes = Encoding.UTF8.GetBytes(json);
        byte[] lengthPrefix = BitConverter.GetBytes(headerBytes.Length);
        if (BitConverter.IsLittleEndian) Array.Reverse(lengthPrefix);   // 转大端

        var ms = new MemoryStream();
        ms.Write(lengthPrefix, 0, 4);
        ms.Write(headerBytes, 0, headerBytes.Length);
        ms.Write(payload, 0, payload.Length);
        return ms.ToArray();
    }

    static byte[] ToWavBytes(AudioClip clip)
    {
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);

        using var ms = new MemoryStream();
        using var writer = new BinaryWriter(ms);

        int dataSize = samples.Length * 2;
        writer.Write(Encoding.ASCII.GetBytes("RIFF"));
        writer.Write(36 + dataSize);
        writer.Write(Encoding.ASCII.GetBytes("WAVEfmt "));
        writer.Write(16);
        writer.Write((short)1);
        writer.Write((short)clip.channels);
        writer.Write(clip.frequency);
        writer.Write(clip.frequency * clip.channels * 2);
        writer.Write((short)(clip.channels * 2));
        writer.Write((short)16);
        writer.Write(Encoding.ASCII.GetBytes("data"));
        writer.Write(dataSize);

        foreach (float s in samples)
            writer.Write((short)(Mathf.Clamp(s, -1f, 1f) * short.MaxValue));

        return ms.ToArray();
    }

    async void OnDestroy()
    {
        if (ws != null && ws.State == WebSocketState.Open)
            await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "退出", CancellationToken.None);
        ws?.Dispose();
    }
}