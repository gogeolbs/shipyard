"""
Fabric tasks to configure network in hosts containers

For a list of tasks: fab --list
For help on a task: fab help:<task>
"""

from fabric.decorators import task
from fabric.api import settings, hide, env, execute, run, cd
from config import Config

try:
  config = Config()

  env.user = config['user']
  env.password = config['pass']
  docker_bridge = config['docker_bridge']
  net_interface = config['net_interface']
except Exception, e:
  docker_bridge = 'docker0'
  net_interface = 'eth0'

def testRemote(array):
  output = run(' '.join(array))
  print 'output', output

def test(host):
  execute(testRemote, ['ls', '-lah'], hosts = [host])

def remoteCommand(container_ip, default_gateway, container_name):
  with hide('running', 'stdout', 'stderr'), cd('/opt/pipework'), settings(warn_only = True):
    command = 'sudo ./pipework {} -i {} {} {}/24@{}'.format(docker_bridge,
        net_interface, container_name, container_ip, default_gateway)
    output = run(command)
    return output

@task
def command(host, container_name, container_ip):
  """
  Execute a command in host
  """
  try:
    ip_pattern = '.'.join(container_ip.split('.')[:3])
    default_gateway = '{}.1'.format(ip_pattern)
    print '*******************************'
    print 'host --> {}'.format(host)
    print 'container_name --> {}'.format(container_name)
    print 'container_ip --> {}'.format(container_ip)
    execute(remoteCommand, container_ip, default_gateway, container_name, hosts = [host])
    print ''
    print '*******************************'
  except Exception, e:
    print 'Error in command {}'.format(e)
