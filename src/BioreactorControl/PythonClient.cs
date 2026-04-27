using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;

public class PythonMotorClient
{
    private readonly HttpClient http = new();
    private readonly string baseUrl =
        System.Environment.GetEnvironmentVariable("MOTORCONTROL_BASE_URL")
        ?? "http://127.0.0.1:8000/api";

    public Task MoveAbsolute(string motor, float target, float rate)
    {
        return PostAndEnsureAsync("/motor/move-absolute", new { motor, target, rate });
    }

    public Task MoveRelative(string motor, float distance, float rate)
    {
        return PostAndEnsureAsync("/motor/move-relative", new { motor, distance, rate });
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
        int maxRetries = 5;
        int retryDelayMs = 100; // Wait 100ms between attempts

        for (int i = 0; i < maxRetries; i++)
        {
            var response = payload is null
                ? await http.PostAsync($"{baseUrl}{path}", null)
                : await http.PostAsJsonAsync($"{baseUrl}{path}", payload);

            if (response.IsSuccessStatusCode)
            {
                return; // Success!
            }

            // If the motor is busy (409), wait and try again
            if (response.StatusCode == System.Net.HttpStatusCode.Conflict)
            {
                if (i < maxRetries - 1) 
                {
                    await Task.Delay(retryDelayMs);
                    continue; 
                }
                throw new HttpRequestException($"Motor is persistently busy: {path}");
            }

            // For other errors (404, 500), fail immediately
            response.EnsureSuccessStatusCode();
        }
    }
}
