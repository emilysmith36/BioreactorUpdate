using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;

public class PythonMotorClient
{
    private readonly HttpClient _http = new HttpClient();
    private readonly string _baseUrl = "http://localhost:8000/api";

    public async Task MoveAbsolute(string motor, float target)
    {
        Console.WriteLine("move absolute in python client: ", _baseUrl, "/motor/move-absolute");
        await _http.PostAsJsonAsync($"{_baseUrl}/motor/move-absolute",
            new { motor, target });
    }

    public async Task MoveRelative(string motor, float distance)
    {
        await _http.PostAsJsonAsync($"{_baseUrl}/motor/move-relative",
            new { motor, distance });
    }

    public async Task JogStart(string motor, float rate, string direction)
    {
        await _http.PostAsJsonAsync($"{_baseUrl}/motor/jog-start",
            new { motor, rate, direction });
    }

    public async Task JogStop(string motor)
    {
        await _http.PostAsJsonAsync($"{_baseUrl}/motor/jog-stop",
            new { motor });
    }

    public async Task StopAll()
    {
        await _http.PostAsync($"{_baseUrl}/motor/stop", null);
    }
}