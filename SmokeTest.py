import boto3
import paramiko
import os
import time
import io

# AWS credentials are passed via environment variables
ec2 = boto3.resource('ec2', region_name='us-east-1')
instance = ec2.create_instances(
    ImageId='ami-04ae724346b173455',
    MinCount=1, MaxCount=1,
    InstanceType='t2.large',
    KeyName='my-key-pair',
    SecurityGroupIds=['sg-06decb6229594c4dc'],
)[0]

instance.wait_until_running()
instance.load()
ip = instance.public_ip_address

# Wait for SSH to become available
time.sleep(30)

# SSH setup
private_key_file = io.StringIO(os.getenv('SSH_PRIVATE_KEY'))
key = paramiko.RSAKey.from_private_key(private_key_file)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, username='ec2-user', pkey=key)

# Run commands
cmds = [
    'cd /home/ec2-user',
    'cd devops-final && sudo git pull && sudo docker compose up -d'
]
for cmd in cmds:
    ssh.exec_command(cmd)
    time.sleep(10)  # Allow time for setup

# Test services
for port in [5173, 8080]:
    stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" localhost:{port}')
    if stdout.read().decode().strip() != '200':
        print(f'Port {port} check failed')
        break
else:
    print('Smoke test passed')

# Terminate instance
instance.terminate()
ssh.close()