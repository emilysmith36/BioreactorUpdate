using System;
using System.Collections.Generic;
using System.Text;

namespace BioreactorUI.Models
{
    public class MotorModel
    {
        public int ID { get; set; }
        public bool Connected { get; set; }
        public string StatusMessage { get; set; }

        public MotorModel(int id)
        {
            ID = id;
            Connected = true; // change later
            StatusMessage = $"Printing Data for Motor of ID: {id} Connected?: {Connected}";
        }
    }
}