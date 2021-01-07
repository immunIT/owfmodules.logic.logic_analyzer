# -*- coding: utf-8 -*-

# Octowire Framework
# Copyright (c) ImmunIT - Jordan Ovrè / Paul Duncan
# License: Apache 2.0
# Paul Duncan / Eresse <pduncan@immunit.ch>
# Jordan Ovrè / Ghecko <jovre@immunit.ch>

import csv
import os
import time

from octowire_framework.module.AModule import AModule
from octowire.logic import Logic


class LogicAnalyzer(AModule):
    def __init__(self, owf_config):
        super(LogicAnalyzer, self).__init__(owf_config)
        self.meta.update({
            'name': 'Logic Analyzer',
            'version': '1.0.2',
            'description': 'Collect samples on 8 GPIO channels (GPIO8-GPIO15) and save the result in a '
                           'CSV file for analysis in pulseview',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "trigger_gpio_pin": {"Value": "", "Required": True, "Type": "int",
                                 "Description": "Trigger sniffing when a change is detected on the configured\n"
                                                "GPIO pin. Setting the trigger to an invalid pin number\n"
                                                "(16 or higher) will start the sniffing process immediately,\n"
                                                "without waiting for any I/O change",
                                 "Default": 16},
            "samples": {"Value": "", "Required": True, "Type": "int",
                        "Description": "The number of samples to collect (maximum: 131072)", "Default": 131072},
            "samplerate": {"Value": "", "Required": True, "Type": "int",
                           "Description": "The sample rate. 1 000 000 = 1MSPS\n"
                                          "(maximum: 3 000 000 -> 3MSPS). Valid values:\n"
                                          "3 000 000 (3MSPS), 1 000 000 (1MSPS), 500 000 (500kSPS), 100 000 (100kSPS)",
                           "Default": 1000000},
            "channels": {"Value": "", "Required": True, "Type": "int",
                         "Description": "The number of channels to save in the output file.",
                         "Default": 8},
            "output_file": {"Name": "output_file", "Value": "", "Required": True, "Type": "file_w",
                            "Description": "The output filename.", "Default": ""}
        }

    @staticmethod
    def get_bits(samples):
        arr = []
        for i in range(8):
            arr.append((samples >> i) & 1)
        return arr

    def params_validator(self, trigger, samples, samplerate, channels):
        if trigger < 0:
            self.logger.handle("Trigger GPIO pin must be >= 0. Setting it to an invalid pin number (16 or higher) will "
                               "start the sniffing process immediately, without waiting for any I/O change.",
                               self.logger.ERROR)
            return False
        if samples not in range(1, 131073):
            self.logger.handle("The number of samples must be defined between 1 and 131072.", self.logger.ERROR)
            return False
        if samplerate not in [100000, 500000, 1000000, 3000000]:
            self.logger.handle("The sample rate should be 100000, 500000, 1000000 or 3000000).", self.logger.ERROR)
            return False
        if channels not in range(1, 9):
            self.logger.handle("The channels parameter must be defined between 1 and 8", self.logger.ERROR)
            return False
        return True

    def get_samples(self):
        trigger_gpio_pin = self.options["trigger_gpio_pin"]["Value"]
        samples = self.options["samples"]["Value"]
        samplerate = self.options["samplerate"]["Value"]
        channels = self.options["channels"]["Value"]
        output_file = self.options["output_file"]["Value"]

        if os.path.splitext(output_file)[1].upper() != '.CSV':
            output_file = output_file + '.csv'

        if self.params_validator(trigger_gpio_pin, samples, samplerate, channels):
            logic_instance = Logic(serial_instance=self.owf_serial)
            self.logger.handle("Sniffing samples...", self.logger.INFO)
            start_time = time.time()
            samples = logic_instance.sniff(trigger_gpio_pin=trigger_gpio_pin, samples=samples, samplerate=samplerate)
            self.logger.handle("Saving results to CSV file...", self.logger.INFO)
            with open(output_file, 'w', newline='') as file:
                writer = csv.writer(file)
                for sample_byte in samples:
                    bits = self.get_bits(sample_byte)[0:channels]
                    writer.writerow(bits)
            logic_instance.logger.handle("Use the following command line to open the capture with pulseview: "
                                         "'pulseview(.exe) -i {} -I csv:samplerate={}'".format(output_file, samplerate),
                                         logic_instance.logger.SUCCESS)

    def run(self):
        """
        Main function.
        Run a logic capture and save samples to a CSV file which can be opened with pulseview.
        :return: Nothing.
        """
        # If detect_octowire is True then detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. This sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return
        try:
            self.get_samples()
        except (Exception, ValueError) as err:
            self.logger.handle(err, self.logger.ERROR)
