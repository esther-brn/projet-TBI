# -*- coding: utf-8 -*-
"""
Created on Wed Dec 18 09:48:52 2024

@author: Esther
"""

import serial
import time
import re


class MX_valve():
    """
    Class to control MXII valves.
    
    """
     
    def __init__(self, address, ports = 10, name = '', verbose = False,  baudrate = 19200):
        '''
        Input:
        `Address`: address of valve : 'COMX' on windows.
        `Ports` (int): Number of ports, default = 10.
        `Name` (str): Name to identify valve for user (not necessary).
        `baudrate` (int): Baudrate for communication, default 19200.
            Other options: 9600, 19200, 38400, 57600.
        
        '''
        self.address = address
        self.ports = ports
        self.name = name
        self.ser = serial.Serial(address, timeout = 2, baudrate = baudrate, 
                   write_timeout=5)
        self.verbose = verbose
        self.verboseprint = print if self.verbose else lambda *a, **k: None

    def stripped_hex(self, target):
        """
        Function to convert a decimal to a hexadecimal but without the "0x" and
        capitalized
        Input:
            `target` (int): Decimal to cenvert to stripped hex
        Output: Striped hexadecimal

        The normal python hex() functions returns a hex including the "0x" and
        in lower case. This should work for all lengths of integer decimals

        """
        result = hex(target)
        result = result[-(len(result) - 2):]
        result = result.upper()
        return result

    def wait_ready(self):
        """
        Function that repeatedly asks the valve if it is ready for new input.
        
        """
        msg = self.message_builder('read')
        self.read_message() 
        while True:
            self.write_message(msg)
            response = self.read_message()
            if response != b'**':
                break

    def message_builder (self, objective, port = 1):
        """
        Build and format message for MXII valve
        Imput:
        `objective` (str): 'change' to change port. 'read' to get current port
        `port` (int): port number to change to
        
        """
        message = ''
        if objective == 'change':
            message += 'P0' #"P" = command to read, "0" part of the port 
            message += self.stripped_hex(port) #hex value of the port
        elif objective == 'read':
            message += 'S' #"S" = read the current valve position.

        message += '\r' #escape character at the end of every message
        message = message.encode('ascii')
        return message
        

    def read_message(self):
        """
        Read response of the valve.
        Output: response of the pump.
        
        """
        n = self.ser.inWaiting()
        time.sleep(0.05) #Alow valve to process
        response = self.ser.read(n)
        time.sleep(0.05) #Alow valve to process
        return response
    
    def write_message(self, message):
        """
        Write message to the MXII valve. 
        Input:
        `message`: Message to sent to valve
            
        """
        self.read_message() 
        self.ser.write(message)
        time.sleep(0.05)
    
    def response_interpret(self, response):
        '''
        Interpret the messages from the MXII valve. Only two responses possible:
            (1) Current port
            (2) Valve ready
        Input: 
        `response` = response from the pump as byte
        Output either:
        (1): current port (int)
        (2): pump status (bool), if ready returns True, if bussy returns False
        
        '''
        port_val = re.compile(b'0.\\r')
        err_val = re.compile
        if re.match(port_val, response):
            current_port = int(chr(response[1]), 16)
            return int(current_port)
        elif response == b'\r':
            return True
        # Valve busy
        elif response == b'*' or response == b'**':
            return False
        elif response == b'':
            raise ValueError(f'The {self.name} valve did not send a response back. This probably indicates that it is not properly connected.')
        else:
            print(''' You have an unknown error.''')
            raise ValueError('Unknown valve response: "{}", can not interpret'.format(response))

    def get_port(self):
        """
        Read the current port position of the valve. 
        Returns:
        Current port

        """
        msg = self.message_builder('read')
        self.write_message(msg)
        response = self.read_message()
        return self.response_interpret(response)
    
    def change_port(self, port):
        """
        Function to change the port of the valve. 
        Input: 
            `port` (int): Port to change to
        Checks if the provided port is valid and checks the current port, it 
        change the port and sleep during the transition time. 
        
        """
        #Check input
        if not isinstance(port, int) or port < 1 or port > self.ports:
            raise ValueError('Invalid port number: {}'.format(port))

        #Check if valve is already in correct position
        current_port = self.get_port()
        if current_port == port:
            self.verboseprint('Valve: "{}" already in position {}'.format(self.name, port))
        
        #Change port
        else:
            while True:
                self.write_message(self.message_builder('change', port))
                self.wait_ready()
                current_port = self.get_port()
                if  current_port == port:
                    self.verboseprint('Valve: "{}" moved to port {}'.format(self.name, current_port))
                    break