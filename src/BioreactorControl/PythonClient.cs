using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;

public class PythonMotorClient
{
    private readonly HttpClient http = new();
    private readonly string baseUrl =
        System.Environment.GetEnvironmentVariable("MOTORCONTROL_BASE_URL")
        ?? "http://127.0.0.1:8000/api";

    public Task MoveAbsolute(string motor, float target)
    {
        return PostAndEnsureAsync("/motor/move-absolute", new { motor, target });
    }

    public Task MoveRelative(string motor, float distance)
    {
        return PostAndEnsureAsync("/motor/move-relative", new { motor, distance });
    }

    public Task JogStart(string motor, float rate, string direction)
    {
        var normalizedDirection = direction switch
        {
            "-1" => "down",
            "1" => "up",
            _ => direction.ToLowerInvariant()
        };

        return PostAndEnsureAsync("/motor/jog-start", new
        {
            motor,
            rate,
            direction = normalizedDirection
        });
    }

    public Task JogStop(string motor)
    {
        return PostAndEnsureAsync("/motor/jog-stop", new { motor });
    }

    public Task StopAll()
    {
        return PostAndEnsureAsync("/system/abort", null);
    }

    private async Task PostAndEnsureAsync(string path, object? payload)
    {
        HttpResponseMessage response = payload is null
            ? await http.PostAsync($"{baseUrl}{path}", null)
            : await http.PostAsJsonAsync($"{baseUrl}{path}", payload);

        response.EnsureSuccessStatusCode();
    }
}
