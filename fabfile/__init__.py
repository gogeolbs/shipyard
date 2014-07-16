# Copyright 2014 Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Shipyard Fabric Deployment and Development Tasks

For a list of tasks: fab -l

For help on a task: fab help:<task>
"""


import os
import json
import time
import string
from random import Random


from py.path import local as localpath

import fabric.state
from fabric.decorators import task
from fabric.contrib.files import upload_template
from fabric.context_managers import settings, hide
from fabric.api import sudo, run, env, execute, put, reboot


from . import help  # noqa
from .utils import tobool


fabric.state.output['running'] = False
env.output_prefix = False


TEMPLATES = localpath(__file__).new(basename="templates")


def check_docker(*args, **kwargs):
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        out = run('which docker')
        if out == '':
            install_docker()


def check_valid_os(*args, **kwargs):
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        out = run('which apt-get')
        if out == '':
            raise StandardError('Only Debian/Ubuntu are currently supported.  Sorry.')


def get_local_ip():
    return run("ifconfig eth0 | grep 'inet addr:' | cut -d':' -f2 | awk '{ print $1; }'")


@task
def install_core_dependencies():
    check_valid_os()
    print(':: Installing Core Dependencies on {}'.format(env.host_string))
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        sudo('apt-get update')
        sudo('apt-get -y upgrade')
        sudo('apt-get install -y curl wget supervisor')

@task
def install_openvswitch():
    check_valid_os()
    print(':: Installing Open vSwitch on {}'.format(env.host_string))
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        sudo('add-apt-repository universe')
        sudo('add-apt-repository multiverse')
        sudo('apt-get update')
        ver = run('cat /etc/lsb-release  | grep DISTRIB_RELEASE | cut -d \'=\' -f2')
        sudo('echo "BRCOMPAT=yes" >> /etc/default/openvswitch-switch')
        if ver == '12.04':
            sudo('apt-get install -y openvswitch-controller openvswitch-brcompat \
                    openvswitch-switch openvswitch-datapath-source')
            sudo('module-assistant auto-install openvswitch-datapath -q')
        else:
            sudo('apt-get install -y openvswitch-switch openvswitch-controller openvswitch-brcompat')
        sudo('service openvswitch-controller restart')
        sudo('service openvswitch-switch restart')
        sudo('wget -O /usr/local/bin/pipework https://s3.amazonaws.com/arcus-docker/support/pipework')
        sudo('chmod +x /usr/local/bin/pipework')

@task
def setup_openvswitch(bridge_name='ovsbr0', internal_bridge_name='ovsbr-int',
        tep_network='172.24.1.0'):
    check_valid_os()
    print(':: Configuring Open vSwitch on {}'.format(env.host_string))
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        out = run('which ovs-vsctl')
        if out == '':
            execute(install_openvswitch)
        sudo('ovs-vsctl add-br {}'.format(bridge_name))
        sudo('ovs-vsctl add-br {}'.format(internal_bridge_name))
        hostname = run('hostname -s | md5sum | head -c 8')
        host_ip = run("ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'")
        tep_name = 'tep-{}'.format(hostname)
        tep_ip = '{}.{}'.format('.'.join(tep_network.split('.')[0:2]),
                host_ip.split('.')[-1])
        gre_name = 'gre-{}'.format(hostname)
        sudo('ovs-vsctl add-port {0} {1} -- set interface {1} type=internal'.format(
            bridge_name, tep_name))
        sudo('ifconfig {} {} netmask 255.255.255.0'.format(
            tep_name, tep_ip))
        tep_ips = []
        host_ips = []
        current_host = env.host_string
        # loop through hosts to get tep_ips
        # i'm sure this isn't efficient but this is the best way i could get
        # with the way fabric handles hosts
        for host in env.hosts:
            env.host_string = host
            host_ip = run("ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'")
            host_ips.append(host_ip)
            tep_ip = '{}.{}'.format('.'.join(tep_network.split('.')[0:-1]),
                    host_ip.split('.')[-1])
            tep_ips.append(tep_ip)
        env.host_string = current_host
    # loop through all hosts and setup the GRE tunnels
    current_host = env.host_string
    for host in env.hosts:
        env.host_string = host
        with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
            hostname = run('hostname -s | md5sum | head -c 8')
            host_ip = run("ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'")
            gre_name = 'gre-{}'.format(hostname)
            tep_ip = '{}.{}'.format('.'.join(tep_network.split('.')[0:-1]),
                    host_ip.split('.')[-1])
            for ip in host_ips:
                if ip != host_ip:
                    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
                        sudo('ovs-vsctl add-port {0} {1} -- set interface {1} type=gre \
                                options:remote_ip={2}'.format(
                                    internal_bridge_name, gre_name, ip))
    env.host_string = current_host

@task
def clean_openvswitch(bridge_name='ovsbr0', internal_bridge_name='ovsbr-int'):
    check_valid_os()
    print(':: Cleaning Open vSwitch on {}'.format(env.host_string))
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        hostname = run('hostname -s | md5sum | head -c 8')
        tep_name = 'tep-{}'.format(hostname)
        gre_name = 'gre-{}'.format(hostname)
        sudo('ovs-vsctl del-port {} {}'.format(bridge_name, tep_name))
        sudo('ovs-vsctl del-port {} {}'.format(bridge_name, gre_name))
    with settings(warn_only=True), hide('stdout', 'running', 'warnings'):
        sudo('ovs-vsctl del-br {}'.format(bridge_name))
        sudo('ovs-vsctl del-br {}'.format(internal_bridge_name))
    

@task
def install_docker():
    check_valid_os()
    print(':: Installing Docker on {}'.format(env.host_string))
    ver = run('cat /etc/lsb-release  | grep DISTRIB_RELEASE | cut -d \'=\' -f2')
    reboot_needed = False
    sudo('apt-get update')
    sudo('sh -c "echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"')
    sudo('sudo sh -c "wget -qO- https://get.docker.io/gpg | apt-key add -"')
    # extras
    if ver == '12.04':
        sudo('apt-get install -y linux-image-generic-lts-raring linux-headers-generic-lts-raring')
        reboot_needed = True
    else:
        sudo('apt-get install -y linux-image-extra-`uname -r`')
    sudo('apt-get update')
    # docker
    sudo('apt-get install -y lxc-docker git-core')
    sudo('echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf ; sysctl -p /etc/sysctl.conf')
    # check ufw
    sudo("sed -i 's/^DEFAULT_FORWARD_POLICY.*/DEFAULT_FORWARD_POLICY=\"ACCEPT\"/g' /etc/default/ufw")
    sudo('service ufw restart')
    # set to listen on local addr
    with open('.tmpcfg', 'w') as f:
        f.write('DOCKER_OPTS="-H unix:///var/run/docker.sock -H tcp://127.0.0.1:4243"')
    put('.tmpcfg', '/etc/default/docker', use_sudo=True)
    os.remove('.tmpcfg')
    sudo('service docker restart')
    if reboot_needed:
        print(':: Setup complete.  Rebooting to apply new kernel...')
        reboot(wait=120)


@task
def setup_redis():
    check_valid_os()
    check_docker()
    print(':: Setting up Shipyard Redis on {}'.format(env.host_string))
    with hide('stdout', 'warnings'):
        build = True
        with settings(warn_only=True):
            out = sudo('docker ps | grep shipyard_redis')
            build = out.return_code
        if build:
            sudo('docker pull shipyard/redis')
            sudo('docker run -i -t -d -p 6379:6379 -name shipyard_redis shipyard/redis')


@task
def setup_app_router(redis_host=None):
    if not redis_host:
        redis_host = env.host_string
    check_valid_os()
    check_docker()
    print(':: Setting up Shipyard Router on {}'.format(env.host_string))
    with hide('stdout', 'warnings'):
        build = True
        with settings(warn_only=True):
            out = sudo('docker ps | grep shipyard/router')
            build = out.return_code
        if build:
            sudo('docker pull shipyard/router')
            c_id = sudo('docker run -i -t -name shipyard_router -d -p 80 -e REDIS_HOST={} shipyard/router'.format(redis_host))
        else:
            c_id = sudo("docker ps | grep shipyard/router | tail -1 | awk '{ print $1; }'")
        port_map = sudo('docker port {} 80'.format(c_id))
        port = port_map.split(':')[-1]
        print('-  Shipyard Router started')
    return '{}:{}'.format(env.host_string, port)


@task
def setup_load_balancer(redis_host=None, upstreams=''):
    check_valid_os()
    check_docker()
    if not redis_host or not upstreams:
        # setup on this host
        execute(setup_redis)
        ret = execute(setup_app_router, env.host_string)
        h, upstream = ret.popitem()
        upstreams = upstream
    # setup upstreams
    print(':: Setting up Shipyard Load Balancer on {}'.format(env.host_string))
    with hide('stdout', 'warnings'):
        build = True
        with settings(warn_only=True):
            out = sudo('docker ps | grep shipyard_lb')
            build = out.return_code
        if build:
            sudo('docker pull shipyard/lb')
            sudo('docker run -i -t -d -p 80:80 -name shipyard_lb -e REDIS_HOST={} -e APP_ROUTER_UPSTREAMS={} shipyard/lb'.format(redis_host, upstreams))
            print('-  Shipyard Load Balancer started')
            print('-  Update DNS to use {} for your Shipyard Domain'.format(env.host_string))


@task
def setup_shipyard_db(db_pass=None):
    check_valid_os()
    check_docker()
    print(':: Setting up Shipyard DB on {}'.format(env.host_string))
    if not db_pass:
        db_pass = ''.join(Random().sample(string.letters+string.digits, 8))
    with hide('stdout', 'warnings'):
        build = True
        with settings(warn_only=True):
            out = sudo('docker ps | grep shipyard_db')
            build = out.return_code
        if build:
            sudo('docker pull shipyard/db')
            sudo('docker run -i -t -d -p 5432 -e DB_PASS={} -name shipyard_db shipyard/db'.format(db_pass))
            print('-  Shipyard DB started')


@task
def setup_shipyard_agent(shipyard_url, version='v0.0.9'):
    check_valid_os()
    check_docker()
    print(':: Setting up Shipyard Agent on {}'.format(env.host_string))
    with hide('stdout', 'warnings'):
        sudo('apt-get install -y supervisor')
        with settings(warn_only=True):
            sudo('supervisorctl stop shipyard-agent')
        url = 'https://github.com/shipyard/shipyard-agent/releases/download/{}/shipyard-agent'.format(version)
        sudo('wget --no-check-certificate {} -O /usr/local/bin/shipyard-agent'.format(url))
        sudo('chmod +x /usr/local/bin/shipyard-agent')
        # register
        out = sudo('/usr/local/bin/shipyard-agent -url {} -register'.format(
            shipyard_url))
        agent_key = out.split('\n')[-1].split(':')[-1].strip()

        # configure supervisor
        upload_template(
            str(TEMPLATES.join("shipyard-agent.conf")),
            "/etc/supervisor/conf.d/shipyard-agent.conf",
            context={"url": shipyard_url, "key": agent_key},
            use_sudo=True,
        )
        sudo('supervisorctl update')


@task
def setup_shipyard(redis_host=None, admin_pass=None, tag='latest', debug=False):
    check_valid_os()
    check_docker()
    if not redis_host:
        redis_host = env.host_string

    print(':: Setting up Shipyard on {}'.format(env.host_string))
    with hide('stdout', 'warnings'):
        build = True
        with settings(warn_only=True):
            out = sudo('docker ps | grep shipyard/shipyard')
            build = out.return_code
        if build:
            sudo('docker pull shipyard/shipyard')
            sudo(
                'docker run -i -t -d \
                -p 8000:8000 -link shipyard_db:db -e DEBUG={} -e REDIS_HOST={} -e ADMIN_PASS={} -name shipyard \
                shipyard/shipyard:{} app master-worker'.format("True" if debug else "False", redis_host, admin_pass, tag)
            )
            print('-  Shipyard started with credentials: admin:{}'.format(admin_pass))
            while True:
                with settings(warn_only=True):
                    out = run('wget -O- --connect-timeout=1 http://{}:8000/'.format(env.host_string))
                    if out.find('Shipyard Project') != -1:
                        break
                    time.sleep(1)
            run('hostname -s')
            user_json = run('curl -d "username=admin&password={}" http://{}:8000/api/login'.format(admin_pass, env.host_string))
            user_data = json.loads(user_json)
            api_key = user_data.get('api_key')
            # get list of hosts to activate
            host_json = run(
                'curl -H "Authorization: ApiKey admin:{}" -H "Content-type: application/json" http://{}:8000/api/v1/hosts/'.format(
                    api_key, env.host_string
                )
            )
            host_data = json.loads(host_json)
            hosts = host_data.get('objects')
            # activate
            for host in hosts:
                    host_data = {
                        'enabled': True,
                    }
                    # authorize host
                    run(
                        'curl -H "Authorization: ApiKey admin:{}" -X PUT -d \'{}\' -H "Content-type: application/json" http://{}:8000/api/v1/hosts/{}/'.format(
                            api_key, json.dumps(host_data), env.host_string, host.get('id')
                        )
                    )
        print('-  Shipyard available on http://{}:8000'.format(env.host_string))


@task()
def setup(**options):
    """Setup a full production deployment

    Options:
        tag         - "latest" or "dev" or any valid git tag.
        debug       - Whether or not to deploy a debug deployment (Default: no)
        password    - An optional admin password. (Default is to randomly generate one)
    """

    tag = options.get("tag", "latest")
    password = options.get("password", None)
    debug = tobool(options.get("debug", "no"))

    # setup redis
    execute(install_core_dependencies)
    # redis
    execute(setup_redis)
    # setup app router
    ret = execute(setup_app_router, env.host_string)
    h, upstream = ret.popitem()
    # setup lb
    execute(setup_load_balancer)

    # setup shipyard

    # generate db_pass
    db_pass = ''.join(Random().sample(string.letters+string.digits, 8))

    # generate or use provided admin pasword
    admin_pass = password or ''.join(Random().sample(string.letters+string.digits, 12))

    # shipyard db
    execute(setup_shipyard_db, db_pass)
    # shipyard
    execute(setup_shipyard, admin_pass=admin_pass, tag=tag, debug=debug)
    # install agent
    execute(setup_shipyard_agent, 'http://{}:8000'.format(env.host_string))


@task
def teardown():
    env.warn_only = True
    with hide('stdout', 'warnings'):
        print(':: Tearing down Shipyard Redis')
        sudo('docker kill shipyard_redis')
        sudo('docker rm shipyard_redis')
        print(':: Tearing down Shipyard Load Balancer')
        sudo('docker kill shipyard_lb')
        sudo('docker rm shipyard_lb')
        print(':: Tearing down Shipyard Router')
        sudo('docker kill shipyard_router')
        sudo('docker rm shipyard_router')
        print(':: Tearing down Shipyard DB')
        sudo('docker kill shipyard_db')
        sudo('docker rm shipyard_db')
        print(':: Tearing down Shipyard')
        sudo('docker kill shipyard')
        sudo('docker rm shipyard')


@task
def check_env(lb_host=None, core_host=None):
    env.warn_only = True
    with hide('warnings'):
        env.host_string = lb_host
        sudo('docker ps | grep shipyard/redis')
        sudo('docker ps | grep shipyard/lb')
        env.host_string = core_host
        sudo('docker ps | grep shipyard/router')
        sudo('docker ps | grep shipyard/db')
        sudo('docker ps | grep shipyard/shipyard')


@task
def clean():
    env.warn_only = True
    execute(teardown)
    with hide('stdout', 'warnings'):
        print(':: Removing images')
        sudo('docker rmi shipyard/redis')
        sudo('docker rmi shipyard/lb')
        sudo('docker rmi shipyard/router')
        sudo('docker rmi shipyard/db')
        sudo('docker rmi shipyard/shipyard')
