using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

public class WsEchoTest : MonoBehaviour
{
    private ClientWebSocket ws;

    async void Start()
    {
        ws = new ClientWebSocket();
        try
        {
            await ws.ConnectAsync(new Uri("ws://localhost:8765"), CancellationToken.None);
            Debug.Log("WebSocket 已连接");
            await SendAndReceive("你好，Nagi");
        }
        catch (Exception e)
        {
            Debug.LogError($"WebSocket 出错：{e.Message}");
        }
    }

    async Task SendAndReceive(string message)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(message);
        await ws.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
        Debug.Log($"[发送] {message}");

        var buffer = new byte[1024];
        var result = await ws.ReceiveAsync(buffer, CancellationToken.None);
        string reply = Encoding.UTF8.GetString(buffer, 0, result.Count);
        Debug.Log($"[收到回声] {reply}");
    }

    async void OnDestroy()
    {
        if (ws != null && ws.State == WebSocketState.Open)
            await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "退出", CancellationToken.None);
        ws?.Dispose();
    }
}