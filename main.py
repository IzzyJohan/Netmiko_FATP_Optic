import time
from netmiko import ConnectHandler, SSHDetect, redispatch
import json
import logging

def config_data():
    with open('config.json', 'r') as read_file:
        config_data = json.load(read_file)
        global jumpserver, node
        jumpserver = config_data['jumpserver']
        node = config_data['node']

def jumpserver_connection():
    guesser = SSHDetect(**jumpserver)
    best_match = guesser.autodetect() # Automatic device type detector
    # print(guesser.potential_matches) # Netmiko dictionary of device match
    jumpserver['device_type'] = best_match

    global net_connect
    net_connect = ConnectHandler(**jumpserver)
    print(f'Jump Server Prompt: {net_connect.find_prompt()}\n')

    log_file()
    node_connection(get_ip_list())

    net_connect.write_channel('exit\n')
    log_file.close

def log_file():
    file_name = input('Masukan nama file: ')
    print()
    global log_file
    log_file = open(f'{file_name}.log', 'w')

def debugging_log():
    logging.basicConfig(filename='debug.log', level=logging.DEBUG)

def separator():
        separator = '=-' * 42 
        return separator

def get_ip_list():
    with open('ip_list.txt', 'r') as read_file:
        ip_list = read_file.read().splitlines()
    stripped_ip_list = [ip.strip() for ip in ip_list]
    while('' in stripped_ip_list):
        stripped_ip_list.remove('')
    return(stripped_ip_list)

def create_json_file(template, filename='data.json'):
    with open(filename, 'w') as created_file:
        json_string = json.dumps(template)
        created_file.write(json_string)

def insert_to_json(data, filename='data.json'):
    with open(filename, 'r+') as read_file:
        json_data = json.load(read_file)
        json_data["nodes"].update(data)
        read_file.seek(0)
        json.dump(json_data, read_file, indent=4)

def json_template():
    template = {
        "nodes": {

        }
    }
    return template

def get_hostname():
    prompt = net_connect.find_prompt()
    hostname = prompt[-19:-1]
    return hostname

def show_up_interface(command='show interface brief | i up'):
    output = net_connect.send_command(command, use_textfsm=True)
    time.sleep(1)
    return output

def insert_data(hostname, output,):
    data = {
            hostname: output
    }
    return data

def interface_string_filter(hostname, filename='data.json'):
    with open(filename, 'r+') as read_file:
        json_data = json.load(read_file)
        node_data_list = json_data['nodes'][hostname]
     
        commands = []
        index = 0
        for item in node_data_list:
            node_data_dict = node_data_list[index]
            interface = list(node_data_dict.values())[0]
            if '.' not in interface:    
                if '/' in interface:
                    optic_param = interface[2::]
                    if '/' in optic_param[1:4]:
                        command = f'show controllers optics {optic_param}'        
                        commands.append(command)
            index += 1
        return commands

def show_optic(commands):
    for command in commands:
        output = f'{net_connect.send_command(command)}\n'
        node_prompt = f'{net_connect.find_prompt()}{command}'
        time.sleep(1)
        print(f'{node_prompt}\n{output}\n')
        log_file.write(f'{node_prompt}\n{output}' + '\n\n')

def show_active_alarm():
    command = 'show alarms brief system active'
    output = f'{net_connect.send_command(command)}\n'
    node_prompt = f'{net_connect.find_prompt()}{command}'
    time.sleep(1)
    print(f'{node_prompt}\n{output}\n')
    log_file.write(f'{node_prompt}\n{output}' + '\n\n')


def active_node_handler():
    net_connect.write_channel(f"{node['password']}\n")
    time.sleep(2)
    net_connect.write_channel(f"{node['another_password']}\n")
    time.sleep(2)

    redispatch(net_connect, device_type=node['device_type'])

    get_hostname()
    show_up_interface()
    node_data = insert_data(hostname=get_hostname(), output=show_up_interface())

    insert_to_json(data=node_data)
    interface_string_filter(hostname=get_hostname())
    show_active_alarm()
    show_optic(commands=interface_string_filter(hostname=get_hostname()))

    net_connect.write_channel('exit\n')
    time.sleep(2)

def node_connection(ip_list):
    for ip in ip_list:

        prompt_view = f"{net_connect.find_prompt()}ssh {node['ssh_user']}@{ip}\n"
        print(prompt_view)
        log_file.write(prompt_view + '\n')

        ssh_command = f"ssh {node['ssh_user']}@{ip}\n"
        net_connect.write_channel(ssh_command)
        time.sleep(3)

        node_respond = net_connect.read_channel()

        if 'yes/no' in node_respond.lower():
            net_connect.write_channel('yes\n')
            time.sleep(2)
            active_node_handler()

        elif 'password' in node_respond.lower():
            active_node_handler()
        
        elif node_respond == ssh_command:
            no_respond = f'{ip} is not responding\n\n'
            print(f'{no_respond}\n')
            log_file.write(no_respond + '\n\n')
            net_connect.write_channel('\3')
            time.sleep(2)

        else:
            print(f'{node_respond}\n')
            log_file.write(node_respond + '\n\n')
            net_connect.write_channel('\3')
            time.sleep(2)

        print(separator())
        log_file.write(separator() + '\n')

def main():
    config_data()
    create_json_file(template=json_template())
    jumpserver_connection()

if __name__ == '__main__':
    main()

