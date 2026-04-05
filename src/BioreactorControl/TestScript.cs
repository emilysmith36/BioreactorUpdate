/*using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using BioreactorControl.Backend;
using BioreactorControl.Motors;
using BioreactorControl.Actions;

class BioreactorTest
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Starting Test Script");

        int numberOfMotors = 3;

        // Create backend
        BackendManagement backend = new BackendManagement();
        await backend.Initialize(); // no per-project data yet

        // Create a list of motor controllers and tasks
        List<MotorController> motors = new();
        List<Task> motorTasks = new();

        for (int i = 0; i < numberOfMotors; i++)
        {
            // Create a motor controller
            var motor = new MotorController(i);
            motors.Add(motor);

            // Build a project for this motor
            var actions = BuildMotorActions();

            // Assign the project to the motor
            motor.CreateProject(actions);

            // Start the motor project with staggered delay
            var task = StartMotorWithDelay(motor, i * 1000); // stagger by 1 sec each
            motorTasks.Add(task);
        }

        // Wait for all motors to finish
        await Task.WhenAll(motorTasks);

        Console.WriteLine("All motor projects complete");
    }

    // Builds the actions list for a motor
    static List<ProjectAction> BuildMotorActions()
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
    static async Task StartMotorWithDelay(MotorController motor, int delayMilliseconds)
    {
        await Task.Delay(delayMilliseconds);
        Console.WriteLine($"Starting Motor {motor.MotorID} project after {delayMilliseconds}ms delay");
        await motor.StartProjectAsync();
    }
}
*/

/*
class BioreactorTest
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Starting Test Script");

        // Setup reactor and project
        ReactorSettings reactor = new ReactorSettings(1, 3);
        ProjectData project = new ProjectData(reactor);

        // Add actions here
        var loop = new LoopAction(3);
        loop.AddAction(new ManualAction(100, 10));
        loop.AddAction(new WaitAction(2));
        loop.AddAction(new ManualAction(0, 10));

        project.actionList.Add(new ManualAction(100, 10));
        project.actionList.Add(new WaitAction(3));
        project.actionList.Add(loop);
        project.actionList.Add(new ManualAction(200, 20));

        // Start backend with this project
        BackendManagement backend = new BackendManagement();
        await backend.Initialize(project);
        await backend.StartProject();
    }
}*/