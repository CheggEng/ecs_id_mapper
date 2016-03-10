# ECS ID Mapper

*Please note, this is still in active development and is of beta quality*

### Overview

ECS ID Mapper is a tool for tracking the relationship between an ECS task ID and a Docker container ID. The tool
also records relevant information about a docker container which can be useful for other tools to query. It has two  
components, an agent that runs on the EC2 host in the ECS cluster and a server.


### Server Methods
The server has a basic REST interface that behaves as follows:


`/query/container_id/<container_id>`
Get the corresponding task id for a given container id. Returns a text string if found, 404 if not found.

`/query/container_id/<container_id>/_all`
Get all known attributes of a container based on container id. Returns JSON if found, 404 if not found.

`/query/container_id/<container_id>/cadvisor`
Get the cadvisor URL for a given container by container_id. Append `?redir=true` to get a 302 redirect to the cAdvisor URL. 

`/query/task_id/<task_id>`
Get the corresponding container id for a given task id. Returns a text string if found, 404 if not found.

`/query/container_id/<task_id>/_all`
Get all known attributes of a container based on task id. Returns JSON if found, 404 if not found.

`/query/container_id/<task_id>/cadvisor`
Get the cadvisor URL for a given container by task_id. Append `?redir=true` to get a 302 redirect to the cAdvisor URL. 

`/health`
Internal health check of the server, returns 200 if the server is healthy. 


### Architecture 
The agent runs on the EC2 instances that run containers (aka ECS instances) periodically polls the local ECS agent
on port 51678 for information about the containers it is managing on that host. Also polls the EC2 instance metadata
service for information about the instance itself. It then compares the containers reported by ECS agent with its internal 
state of known containers and reports any new containers to the server. The agent also reports the changes in state of 
containers as events regardless of the state being known. 

The server stores information about containers it receives in [AWS SDB](https://aws.amazon.com/simpledb/), and also does 
some processing to generate URLs for monitoring tools for each container it gets reports of.

The server provides REST APIs to users who want to query information in the database.
 
The server runs in a Docker container. Each container is essentially stateless so multiple
containers can be run behind a load balancer for increased availability and throughput.

### Requirements 
* Docker compatible runtime
* [Hashicorp Vault](https://www.vaultproject.io) (for storing secrets)
* [AWS SimpleDB](https://aws.amazon.com/simpledb/)
* [AWS EC2 Container Service](https://aws.amazon.com/ecs/)
* python 2.7 and [python requests](http://docs.python-requests.org/en/master/) (for the agent)

