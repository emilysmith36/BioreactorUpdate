using BioreactorControl.Backend;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using BioreactorControl.Motors;
using BioreactorControl.Projects;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.SetMinimumLevel(LogLevel.Warning); // Reduces logging  noise (was printing every position update)

// Add the backend as a "Singleton" so every API call talks to the SAME motors
builder.Services.AddSingleton<BackendManagement>();

var app = builder.Build();

// 1. Initialize the hardware/motors once at startup
var backendInstance = app.Services.GetRequiredService<BackendManagement>();
Program.Backend = backendInstance;

await Program.Backend.Initialize();

app.MapPost("/api/jog/start", async (JogRequest req, BackendManagement backend) =>
{
    int.TryParse(req.Motor.Replace("Motor ", ""), out int motorNum);
    int index = motorNum - 1;
    var motor = backend.Motors[index];

    await JogStart(req.Rate, req.Direction, index);

    backend.PushEvent(new BioreactorEvent
    {
        Type = "jog_start",
        Motor = motorNum.toString(),
        Message = "Motor jog started",
        Position = null,
        State = "running",
        Step = null,
    });

    return Results.Ok(new { message = "jog started" });
});

app.MapPost("api/jog/stop", async (JogRequest req, BackendManagement backend) =>
{
    int.TryParse(req.Motor.Replace("Motor ", ""), out int motorNum);
    int index = motorNum - 1;
    var motor = backend.Motors[index];

    await JogStop();

    backend.PushEvent(new BioreactorEvent
    {
        Type = "jog_stop",
        Motor = motorNum.toString(),
        Message = "Motor jog stopped",
        Position = null,
        State = "idle",
        Step = null,
    });

    return Results.Ok(new { message = "jog stopped" });
});
