using BioreactorControl.Backend;
using BioreactorControl.Motors;
using BioreactorControl.Projects;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.SetMinimumLevel(LogLevel.Warning);
builder.Services.AddSingleton<BackendManagement>();
builder.Services.AddSingleton<PythonMotorClient>();

var app = builder.Build();

var backendInstance = app.Services.GetRequiredService<BackendManagement>();
Program.Backend = backendInstance;
await Program.Backend.Initialize();

app.MapGet("/api/status", () => Results.Ok("Backend is running"));

app.MapGet("/api/status/all", (BackendManagement backend) =>
    Results.Ok(backend.Motors.Select(m => new
    {
        motor = m.MotorName,
        isRunning = m.State == MotorState.Running,
        isBusy = m.IsBusy,
        position = m.motorPosition,
        state = m.State.ToString().ToLowerInvariant(),
        step = m.CurrentStep
    })));

app.MapGet("/api/events", (BackendManagement backend) =>
    Results.Ok(backend.DequeueEvents()));

app.MapPost("/api/program/load", (ProgramLoadRequest req, BackendManagement backend) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    var actions = req.Steps.Select(step => new CycleBasedAction(
        step.direction,
        step.rate,
        step.frequency_hz,
        step.displacement_mm,
        step.duration_seconds,
        step.estimated_seconds,
        step.cycles,
        step.timing_mode == "cycles",
        step.target_position_mm,
        step.label)).Cast<ProjectAction>().ToList();

    motor.CreateProject(actions);
    return Results.Ok(new { message = $"Loaded {actions.Count} steps" });
});

app.MapPost("/api/program/start", (StartRequest req, BackendManagement backend) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    if (motor.IsBusy)
    {
        return Results.Conflict($"{motor.MotorName} is already busy");
    }

    if (!motor.HasLoadedProject)
    {
        return Results.Conflict($"{motor.MotorName} has no loaded project");
    }

    _ = motor.Start();
    return Results.Ok(new { message = $"{motor.MotorName} sequence started." });
});

app.MapPost("/api/jog/start", async (
    JogRequest req,
    BackendManagement backend,
    PythonMotorClient python) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    if (motor.IsBusy)
    {
        return Results.Conflict($"{motor.MotorName} is already busy");
    }

    try
    {
        await python.JogStart(req.Motor, req.Rate, req.Direction);
        await motor.JogStart(req.Rate, ParseDirection(req.Direction));
        return Results.Ok();
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Jog start failed: {ex.Message}");
    }
});

app.MapPost("/api/jog/stop", async (
    JogStopRequest req,
    BackendManagement backend,
    PythonMotorClient python) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    motor.JogStop();

    try
    {
        await python.JogStop(req.Motor);
        return Results.Ok();
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Jog stop failed: {ex.Message}");
    }
});

app.MapPost("/api/motor/move-absolute", async (
    MoveAbsoluteRequest req,
    BackendManagement backend,
    PythonMotorClient python) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    if (motor.IsBusy)
    {
        return Results.Conflict($"{motor.MotorName} is already busy");
    }

    try
    {
        var rate = req.Rate <= 0 ? 1.0f : req.Rate;
        await python.MoveAbsolute(req.Motor, req.Target, rate);
        _ = motor.MoveAbsolute(req.Target, rate);
        return Results.Ok();
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Move absolute failed: {ex.Message}");
    }
});

app.MapPost("/api/motor/move-relative", async (
    MoveRelativeRequest req,
    BackendManagement backend,
    PythonMotorClient python) =>
{
    if (!backend.TryGetMotor(req.Motor, out var motor) || motor is null)
    {
        return Results.BadRequest("Invalid Motor ID");
    }

    if (motor.IsBusy)
    {
        return Results.Conflict($"{motor.MotorName} is already busy");
    }

    try
    {
        var rate = req.Rate <= 0 ? 1.0f : req.Rate;
        await python.MoveRelative(req.Motor, req.Distance, rate);
        _ = motor.MoveRelative(req.Distance, rate);
        return Results.Ok();
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Move relative failed: {ex.Message}");
    }
});

app.MapPost("/api/system/pause", async (
    BackendManagement backend,
    PythonMotorClient python) =>
{
    backend.PauseAll();

    try
    {
        await python.StopAll();
        return Results.Ok("All active motion paused where possible.");
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Pause failed: {ex.Message}");
    }
});

app.MapPost("/api/system/resume", async (
    BackendManagement backend,
    PythonMotorClient python) =>
{
    var jogCommands = backend.ResumeAll();

    try
    {
        foreach (var command in jogCommands)
        {
            await python.JogStart(command.Motor, command.Rate, command.Direction);
        }

        return Results.Ok("Paused motion resumed.");
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Resume failed: {ex.Message}");
    }
});

app.MapPost("/api/system/abort", async (
    BackendManagement backend,
    PythonMotorClient python) =>
{
    backend.EmergencyStopAll();

    try
    {
        await python.StopAll();
        return Results.Ok("All motors halted.");
    }
    catch (HttpRequestException ex)
    {
        return Results.Problem($"Abort failed: {ex.Message}");
    }
});

app.Run();

static int ParseDirection(string direction)
{
    var normalized = direction.Trim().ToLowerInvariant();
    return normalized switch
    {
        "-1" => -1,
        "down" => -1,
        "reverse" => -1,
        "compression" => -1,
        _ => 1
    };
}

public class StartRequest
{
    public string Motor { get; set; } = string.Empty;
}

public class JogStopRequest
{
    public string Motor { get; set; } = string.Empty;
}

public class MoveAbsoluteRequest
{
    public string Motor { get; set; } = string.Empty;
    public float Target { get; set; }
    public float Rate { get; set; } = 1.0f;
}

public class MoveRelativeRequest
{
    public string Motor { get; set; } = string.Empty;
    public float Distance { get; set; }
    public float Rate { get; set; } = 1.0f;
}

public partial class Program
{
    public static BackendManagement Backend { get; set; } = null!;
}
