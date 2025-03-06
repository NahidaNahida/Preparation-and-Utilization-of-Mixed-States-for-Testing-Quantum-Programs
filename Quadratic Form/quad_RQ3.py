from qiskit import QuantumCircuit
 
import numpy as np
import csv

import math

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_convertion import generate_numbers
from quad_specification import PSTC_specification, MSTC_specification
from test_oracle import OPO_UTest
from circuit_execution import circuit_execution

from quad_defect1 import QuadraticForm_defect1
from quad_defect2 import QuadraticForm_defect2
from quad_defect3 import QuadraticForm_defect3
from quad_defect4 import QuadraticForm_defect4
from quad_defect5 import QuadraticForm_defect5
from quad_defect6 import QuadraticForm_defect6

def version_selection(program_name, program_version):
    '''
        select the program version to be tested

        Input variable:
            + program_name       [str] e.g. "IntegerComparator"
            + program_version    [str] e.g. "v1", "v2", "v3"
    
    '''
    if program_version[0] == "v":
        function_name = program_name + '_defect' + program_version[1:]
    elif program_version == 'raw':
        function_name = program_name
    else:
        return f"Invalid program version."

    if function_name in globals():
        func = globals()[function_name]
        return func
    else:
        return f"Function '{function_name}' not found."

def testing_process_PSTCs(program_version, n_list, matA_dict, vecB_dict, c_list, num_out=2, repeats=20):
    program_name = 'QuadraticForm'
    default_shots = 1024
    candidate_initial_states = [0, 1]
    
    recorded_result = []      
    for n in n_list:            
        total_failures = 0
        initial_states = generate_numbers(n, len(candidate_initial_states))
        A_list, b_list = matA_dict[n], vecB_dict[n]
        for _ in range(repeats):
            test_cases = 0
            for c in c_list:
                for A in A_list:
                    for b in b_list:
                        for initial_state in initial_states:
                            test_cases += 1
                            number = int(''.join(map(str, initial_state)), 2)
                            qc = QuantumCircuit(n + num_out, num_out)
                            initial_state = initial_state[::-1]
                            
                            for index, val in enumerate(initial_state):
                                if candidate_initial_states[val] == 1:
                                    qc.x(index)
                                        
                            # append the tested quantum subroutine (quantum program)
                            func = version_selection(program_name, program_version)
                            qc_test = func(num_result_qubits=num_out, quadratic=A, linear=b, offset=c)
                            qc.append(qc_test, qc.qubits)
                            qc.measure(qc.qubits[n:],qc.clbits[:])


                            # execute the program and derive the outputs
                            dict_counts = circuit_execution(qc, default_shots)
                        
                            # obtain the samples (measurement results) of the tested program
                            test_samps = []
                            for (key, value) in dict_counts.items():
                                test_samps += [key] * value
                        
                            # generate the samples that follow the expected probability distribution
                            exp_probs = PSTC_specification(initial_state, A, b, c, num_out)
                            exp_samps = list(np.random.choice(range(2 ** qc.num_clbits), size=default_shots, p=exp_probs))                    

                            # derive the test result by nonparametric hypothesis test
                            test_result = OPO_UTest(exp_samps, test_samps)
                        
                            if test_result == 'fail':
                                total_failures += 1   

        recorded_result.append([n, test_cases, total_failures / test_cases / repeats])
   
    # save the data
    file_name = "RQ3_" + program_name + '_' + program_version + "_PSTC" + ".csv"
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ['n','# test_cases', 'ave_fault']
        writer.writerow(header)
        for data in recorded_result:
            writer.writerow(data)
    print('PSTCs done!')

 
def testing_process_MSTCs(program_version, n_list, matA_dict, vecB_dict, c_list, num_out=2, repeats=20):
    program_name = 'QuadraticForm'
    default_shots = 1024
    
    recorded_result = []    
    for n in n_list:  
        # define the uniform distribution for the ensemble
        pure_states_distribution = list(np.ones(2 ** n) / (2 ** n))
        # cover all the classical states            
        covered_numbers = list(range(2 ** n))
        total_failures = 0
        A_list, b_list = matA_dict[n], vecB_dict[n]
        for _ in range(repeats):
            test_cases = 0
            for c in c_list:
                for A in A_list:
                    for b in b_list:
                        qc = QuantumCircuit(2 * n + num_out, num_out)
                        qc.h(qc.qubits[:n])
                
                        for index in range(n, 2 * n):
                            qc.cx(qc.qubits[index - n], qc.qubits[index])
                        
                        for i in range(n):
                            qc.measure(qc.qubits[i], qc.clbits[-1])

                        # append the tested quantum subroutine (quantum program) 
                        func = version_selection(program_name, program_version)
                        qc_test = func(num_result_qubits=num_out, quadratic=A, linear=b, offset=c)
                        qc.append(qc_test, qc.qubits[n:])
                        qc.measure(qc.qubits[2 * n:],qc.clbits[:])
                        
                        # execute the program and derive the outputs
                        dict_counts = circuit_execution(qc, default_shots)
                    
                        # obtain the samples (measurement results) of the tested program
                        test_samps = []
                        for (key, value) in dict_counts.items():
                            test_samps += [key] * value

                        # generate the samples that follow the expected probability distribution
                        exp_probs = MSTC_specification(covered_numbers, n, A, b, c, num_out, pure_states_distribution)
                        exp_samps = list(np.random.choice(range(2 ** qc.num_clbits), size=default_shots, p=exp_probs))
                                         
                        # derive the test result by nonparametric hypothesis test
                        test_result = OPO_UTest(exp_samps, test_samps)
                            
                        if test_result == 'fail':
                            total_failures += 1
                                
                        test_cases += 1
                
        recorded_result.append([n, test_cases, total_failures / test_cases / repeats])

    # save the data
    file_name = "RQ3_" + program_name + '_' + program_version + "_MSTC" + ".csv"
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ['n','# test_cases', 'ave_fault']
        writer.writerow(header)
        for data in recorded_result:
            writer.writerow(data)
    print('MSTCs done!')

 
if __name__ == '__main__':
    # the setting to generate classical inputs
    n_list = range(2, 6)
    matA_dict = {
        2: [[[0, 0], [0, 1]], 
            [[-1, 2], [1, 1]], 
            [[2, 2], [0, -1]], 
            [[-1, 0], [1, -1]], 
            [[0, 0], [0, -1]]],
        3: [[[0, 0, 1], [0, 1, -1], [1, -1, 2]], 
            [[1, -1, 2], [1, 1, 0], [0, 0, 0]], 
            [[2, 2, 0], [0, -1, -2], [0, 1, -1]], 
            [[0, -1, 0], [1, 1, -1], [1, 2, 1]], 
            [[0, 0, 0], [0, -1, -1], [1, 1, 1]]],
        4: [[[0, 0, 0, 0], [0, 1, 1, 0], [1, 0, 0, 1], [1, 1, 0, 0]], 
            [[-1, 1, 2, 1], [1, 1, 0, 1], [1, 1, 1, 1], [0, 0, 1, 0]], 
            [[2, 2, 2, 2], [0, -1, 0, 0], [1, 1, -2, 1], [0, 0, 0, 0]], 
            [[-1, 0, -1, 0], [1, -1, 1, -1], [0, 1, 0, 1], [1, 2, 1, 2]], 
            [[0, 0, 1, 1], [0, -1, 0, -2], [1, 0, 2, 1], [0, 0, 0, 2]]],
        5: [[[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 0, 1]], 
            [[1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1]], 
            [[-1, 2, 0, 1, 0], [0, -1, 1, -2, 0], [1, -2, 0, 1, 2], [0, 0, 1, 2, 1], [0, 1, 0, 1, 0]], 
            [[-1, 0, -1, 0, -1], [1, -1, 1, -1, 1], [2, -2, 2, -2, 2], [0, 1, 2, 0, 1], [0, 1, 2, 1, 0]], 
            [[0, 0, 0, 1, 0], [0, -1, -1, 0, 2], [2, 1, 0, 1, -1], [1, 1, -1, -1, 0], [0, 0, 0, 1, 0]]]
    }
    vecB_dict = {
        2: [[0, 0], [0, 1], [-1, 2], [1, 1], [2, 2]],
        3: [[0, 0, 1], [0, 1, -1], [1, -1, 2], [1, -1, 2], [1, 1, 0]], 
        4: [[1, -2, 0, 1], [0, 1, 1, 0], [1, 0, 0, 1], [1, 1, 2, 0], [-1, 1, 2, 1]],  
        5: [[1, 1, 1, 1, 1], [-1, 2, 0, 1, 0],  [0, 0, 1, 2, 1], [1, 1, -1, -1, 0], [0, 0, 0, 1, 0]],
    }
    C_list = np.arange(-2, 3, 1)

    # the test processes
    for program_version in ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']:
        print(program_version)
        testing_process_PSTCs(program_version, n_list, matA_dict, vecB_dict, C_list)
        testing_process_MSTCs(program_version, n_list, matA_dict, vecB_dict, C_list)