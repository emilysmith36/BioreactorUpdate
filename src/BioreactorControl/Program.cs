// Program.c - main file:
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using BioreactorControl.Backend;
using BioreactorControl.Motors;
using BioreactorControl.Projects;

Console.WriteLine("Starting Backend");

BackendManagement backend = new BackendManagement();
await backend.Initialize();

// Toggle this to run the test project automatically on startup
bool runTestOnStartup = false;

Task? runTask = null;

if (runTestOnStartup)
{
    // Start the test projects with staggered motors
    runTask = RunStaggeredMotorTest();
}

// Example: simulate emergency stop after 3 seconds
await Task.Delay(3000);
backend.EmergencyStopAll();

// Wait for the motor projects to finish (if started)
if (runTask != null)
{
    await runTask;
}

Console.WriteLine("Backend program completed.");


//////////////////////////
/// Local Functions for testing:
//////////////////////////////////////////

async Task RunStaggeredMotorTest()
{
    int numberOfMotors = 3;
    List<MotorController> motors = new();
    List<Task> motorTasks = new();

    for (int i = 0; i < numberOfMotors; i++)
    {
        var motor = new MotorController(i);
        motors.Add(motor);

        // Create a project for each motor
        var actions = BuildMotorActions();
        motor.CreateProject(actions);  // <-- fixed

        // Start the motor project with a staggered delay (1 sec between motors)
        motorTasks.Add(StartMotorWithDelay(motor, i * 1000));
    }

    await Task.WhenAll(motorTasks);
    Console.WriteLine("All motor projects complete");
}

// Helper to build a sample action list for each motor
List<ProjectAction> BuildMotorActions()
{
    var loop = new LoopAction(3);
    loop.AddAction(new ManualAction(100, 10));
    loop.AddAction(new WaitAction(2));
    loop.AddAction(new ManualAction(0, 10));

    return new List<ProjectAction>
    {
        new ManualAction(100, 10),
        new WaitAction(3),
        loop,
        new ManualAction(200, 20)
    };
}

// Helper to start a motor project with a delay
async Task StartMotorWithDelay(MotorController motor, int delayMilliseconds)
{
    await Task.Delay(delayMilliseconds);
    Console.WriteLine($"Starting Motor {motor.MotorID} project after {delayMilliseconds}ms delay");
    await motor.Start();
}