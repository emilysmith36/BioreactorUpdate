using System.Windows;
using BioreactorUI.Models;

namespace BioreactorUI
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();

            var reactor = new ReactorModel(1, 1);
            var motor = new MotorModel(0);

            OutputText.Text = $"Hello, World!\n" +
                              $"Starting Project\n" +
                              $"Starting Execution Manager\n" +
                              $"Connecting To Reactor\n" +
                              $"Reactor ID: {reactor.ReactorID}\n" +
                              $"Number of Motors: {reactor.NumberOfMotors}\n" +
                              $"Reactor Connection Successful: {reactor.ConnectionSuccessful}\n" +
                              $"Executing Project of ID: 0\n" +
                              $"{motor.StatusMessage}";
        }
    }
}