using System.IO;
using UnityEngine;

public class MicRecorder : MonoBehaviour
{
    private AudioClip recording;
    private bool isRecording;
    private const int SampleRate = 16000;

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.R))
        {
            if (!isRecording) StartRecording();
            else StopRecording();
        }
    }

    void StartRecording()
    {
        if (Microphone.devices.Length == 0)
        {
            Debug.LogError("没有检测到麦克风设备");
            return;
        }
        // 不循环，最长 10 秒，目标采样率 16kHz
        recording = Microphone.Start(Microphone.devices[0], false, 10, SampleRate);
        isRecording = true;
        Debug.Log("录音中……再按一次 R 停止");
    }

    void StopRecording()
    {
        Microphone.End(Microphone.devices[0]);
        isRecording = false;

        // 保存到工程根目录（client-unity/recording.wav）
        string path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "recording.wav"));
        File.WriteAllBytes(path, ToWavBytes(recording));
        Debug.Log($"录音已保存：{path}，时长 {recording.length:F1} 秒，采样率 {recording.frequency} Hz");
    }

    // AudioClip 的 float 采样 → 16 位 PCM WAV 字节流
    static byte[] ToWavBytes(AudioClip clip)
    {
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);

        using var ms = new MemoryStream();
        using var writer = new BinaryWriter(ms);

        int dataSize = samples.Length * 2;
        writer.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));
        writer.Write(36 + dataSize);
        writer.Write(System.Text.Encoding.ASCII.GetBytes("WAVEfmt "));
        writer.Write(16);                                   // PCM 块大小
        writer.Write((short)1);                             // PCM 格式
        writer.Write((short)clip.channels);                 // 声道数
        writer.Write(clip.frequency);                       // 采样率
        writer.Write(clip.frequency * clip.channels * 2);   // 字节率
        writer.Write((short)(clip.channels * 2));           // 块对齐
        writer.Write((short)16);                            // 位深 16bit
        writer.Write(System.Text.Encoding.ASCII.GetBytes("data"));
        writer.Write(dataSize);

        foreach (float s in samples)
            writer.Write((short)(Mathf.Clamp(s, -1f, 1f) * short.MaxValue));

        return ms.ToArray();
    }
}