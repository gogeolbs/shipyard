# Shipyard [![Stories in Ready](https://badge.waffle.io/shipyard/shipyard.png?label=ready)](http://waffle.io/shipyard/shipyard)
Shipyard is a web UI for http://docker.io

# Quickstart
Use the [Quickstart](https://github.com/shipyard/shipyard/wiki/QuickStart) to get
started.

# Help
To report issues please use [Github](https://github.com/shipyard/shipyard/issues)

There is also an IRC channel setup on Freenode:  `irc.freenode.net` `#shipyard`

To deploy a local Shipyard stack:

`docker run -i -t -v /var/run/docker.sock:/docker.sock shipyard/deploy setup`

You should be able to login to http://localhost:8000.  You will need to setup
the [Shipyard Agent](https://github.com/shipyard/shipyard-agent) to see containers,
 images, etc.

Username: admin
Password: shipyard

# Dev Setup
Shipyard uses [Fig](http://orchardup.github.io/fig/) for an easy development environment.  Visit that link first to setup Fig.  Then continue:

* `fig up -d redis router lb db`
* `fig run app python manage.py syncdb --noinput`
* `fig run app python manage.py migrate`
* `fig run app python manage.py createsuperuser`
* `fig up app`
* `fig up worker` (in separate terminal to see output)
* Open browser to localhost:8000 for Shipyard and localhost for the LB (you must not have anything else running on port 80)

To rebuild the app image (if you make changes to the `Dockerfile`, etc.):

* `fig build app`
* `fig build worker`

Then restart the app and worker containers as explained above.

# Deployment

This is another way (different from [here](https://github.com/shipyard/shipyard/wiki/Deployment)) to setup up your production environment with shipyard on multiple hosts.

~~~

        +-----------------------+
        |                       | Host Port Mappings:
        |   shipyard/redis      |
        |                       | 6379 (shipyard/redis)
        |   IP: 192.168.1.3     |
        |                       |
        +-----------+-----------+
                    |
        +-----------v-----------+
        |                       |
        |    shipyard/router    |
        |                       |
        |   IP: 192.168.1.4     |
        |                       |
        +-----------+-----------+
                    |
        +-----------v-----------+
        |                       | Host Port Mappings:
        |      shipyard/lb      |
        |                       | 80   (shipyard/lb)
        |   IP: 192.168.1.5     | 443  (shipyard/lb)
        |                       |
        +-----------+-----------+
                    |
        +-----------v-----------+
        |                       | Host Port Mappings:
        |      shipyard/db      |
        |                       | 5432 (shipyard/db)
        |   IP: 192.168.1.6     |
        |                       |
        +-----------+-----------+
                    |
        +-----------v-----------+
        |                       | Host Port Mappings:
        |   shipyard/shipyard   |
        |                       | 8000 (shipyard/shipyard)
        |   IP: 192.168.1.7     |
        |                       |
        +-----------------------+

~~~

You can see container's network with the command:

~~~ bash
docker inspect --format='{{.NetworkSettings.IPAddress}}' shipyard_redis
~~~

## Launch Redis

~~~ bash
docker run -i -t -d --name shipyard_redis shipyard/redis
~~~

## Launch Router

~~~ bash
docker run -i -t -d -e REDIS_HOST=192.168.1.3 -e REDIS_PORT=6379 --name shipyard_router shipyard/router
~~~

## Launch Load balancer

~~~ bash
docker run -i -t -d -e REDIS_HOST=192.168.1.3 -e REDIS_PORT=6379 -e APP_ROUTER_UPSTREAMS=192.168.1.4 --name shipyard_lb shipyard/lb
~~~

## Launch Shipyard Database

~~~ bash
docker run -i -t -d -e DB_PASS=YOUR_DB_PASS --name shipyard_db shipyard/db
~~~

## Launch Shipyard App

~~~ bash
docker run -i -t -d -e REDIS_HOST=192.168.1.3 -e REDIS_PORT=6379 -e DB_TYPE=postgresql_psycopg2 -e DB_PORT_5432_TCP_ADDR=192.168.1.6 -e DB_PORT_5432_TCP_PORT=5432 -e DB_USER=YOUR_DB_USER -e DB_ENV_DB_PASS=YOUR_DB_PASS -e ADMIN_PASS=YOUR_ADMIN_PASS --name shipyard --entrypoint /app/.docker/run.sh shipyard/shipyard app master-worker
~~~

# Features

* Multiple host support
* Create / Delete containers
* View Images
* Build Images (via uploaded Dockerfile or URL)
* Import repositories
* Private containers
* Container metadata (description, etc.)
* Applications: bind containers to applications that are setup with [hipache](https://github.com/dotcloud/hipache)
* Attach container (terminal emulation in the browser)
* Container recovery (mark container as "protected" and it will auto-restart upon fail/destroy/stop)
* RESTful API
* ...more coming...

# Screenshots

![Login](http://i.imgur.com/8WGsK2Gh.png)

![Containers](http://i.imgur.com/5DAMDw8h.png)

![Container Details](http://i.imgur.com/QFDtF7C.png)

![Container Logs](http://i.imgur.com/k2aZld8h.png)

![Images](http://i.imgur.com/fMXZ92lh.png)

![Applications](http://i.imgur.com/CgSwTRnh.png)

![Hosts](http://i.imgur.com/KC7D1s0h.png)

![Attach Container](http://i.imgur.com/YhiFq1gh.png)

* Note: for attaching to containers you must have access to the docker host.  This
will change in the future.

# API
Shipyard also has a RESTful JSON based API.

See https://github.com/shipyard/shipyard/wiki/API for API details.

# Applications
Applications are groups of containers that are accessible by a domain name.  The easiest
way to test this is to add some local `/etc/hosts` entries for fake domains pointed to `10.10.10.25` (the vagrant vm).  For example, add the following to `/etc/hosts`:

```
10.10.10.25 foo.local
```

Then you can create a new application with the domain `foo.local`.  Attach one or more containers and then access http://foo.local in your browser and it should hit Hipache and be routed to the containers.

For more info on applications, see [here](https://github.com/shipyard/shipyard/wiki/Applications)



# License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
