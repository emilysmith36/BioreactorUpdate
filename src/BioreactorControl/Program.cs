using BioreactorControl.Backend;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using BioreactorControl.Motors;
using BioreactorControl.Projects;




var builder = WebApplication.CreateBuilder(args);

builder.Logging.SetMinimumLevel(LogLevel.Warning); // Reduces logging  noise (was printing every position update)

// Add the backend as a "Singleton" so every API call talks to the SAME motors
builder.Services.AddSingleton<BackendManagement>();

//adding python client as singleton
builder.Services.AddSingleton<PythonMotorClient>();

var app = builder.Build();

// 1. Initialize the hardware/motors once at startup
var backendInstance = app.Services.GetRequiredService<BackendManagement>();
Program.Backend = backendInstance;

await Program.Backend.Initialize();

// --- API ROUTES ---

// Global health check
app.MapGet("/api/status", () => Results.Ok("Backend is running"));

// Get status for a SPECIFIC motor (Fixes the 404 error)
app.MapGet("/api/status/all", (BackendManagement backend) =>
{
    return Results.Ok(backend.Motors.Select(m => new
    {
        motor = $"Motor {m.MotorID + 1}",
        isRunning = m.State == MotorState.Running,
        position = m.motorPosition,
        state = m.State.ToString()
    }));
});

// Event polling for logs and position updates
app.MapGet("/api/events", (BackendManagement backend) =>
    Results.Ok(backend.DequeueEvents()));

// Load Program
app.MapPost("/api/program/load", (ProgramLoadRequest req, BackendManagement backend) =>
{
    if (int.TryParse(req.Motor.Replace("Motor ", ""), out int motorNum))
    {
        int index = motorNum - 1;
        if (index >= 0 && index < backend.Motors.Count)
        {
            var motor = backend.Motors[index];
            var actions = req.Steps.Select(s => new CycleBasedAction(
                s.direction, s.rate, s.frequency_hz, s.displacement_mm,
                s.duration_seconds, s.cycles, s.timing_mode == "cycles"
            )).Cast<ProjectAction>().ToList();

            motor.CreateProject(actions);
            return Results.Ok(new { message = $"Loaded {actions.Count} steps" });
        }
    }
    return Results.BadRequest("Invalid Motor ID");
});

// Add this near your other MapPost routes
app.MapPost("/api/program/start", (StartRequest req, BackendManagement backend) =>
{
    // Convert "Motor 1" -> Index 0
    if (int.TryParse(req.Motor.Replace("Motor ", ""), out int motorNum))
    {
        int index = motorNum - 1;
        if (index >= 0 && index < backend.Motors.Count)
        {
            var motor = backend.Motors[index];

            // Fire and Forget: Start the motor task in the background
            _ = motor.Start();

            return Results.Ok(new { message = $"Motor {motorNum} sequence started." });
        }
    }
    return Results.BadRequest("Invalid Motor ID");
});

////PYTHON ATTEMPTS

app.MapPost("/api/motor/move-absolute", async (
    MoveAbsoluteRequest req,
    PythonMotorClient python) =>
{
    Console.WriteLine("motor move abs backend");
    await python.MoveAbsolute(req.Motor, req.Target);
    return Results.Ok();
});

app.MapPost("api/motor/move-relative", async (
    MoveRelativeRequest req,
    PythonMotorClient python) =>
{
    Console.WriteLine("motor move relative backend");
    await python.MoveRelative(req.Motor, req.Distance);
    return Results.Ok();
});



// Emergency Stop
app.MapPost("/api/system/abort", (BackendManagement backend) =>
{
    backend.EmergencyStopAll();
    return Results.Ok("All motors halted.");
});





// IMPORTANT: This starts the server and BLOCKS here. 
// It won't reach "Application is shutting down" until you hit Ctrl+C.
app.Run();


// Define the tiny helper class for the request
public class StartRequest { public string Motor { get; set; } = string.Empty; }
public class MoveAbsoluteRequest { public string Motor { get; set; } = ""; public float Target { get; set; } }
public class MoveRelativeRequest { public string Motor { get; set; } = ""; public float Distance { get; set; } }

public partial class Program {
    public static BackendManagement Backend { get; set; } = null!;
}

