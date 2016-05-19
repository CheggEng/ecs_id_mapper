## ECS ID Mapper Agent

The agent runs on the ECS Container Instance and queries the ECS agent and the EC2 Metadata services for information.
The container needs to run in host networking mode so it can access the loopback interface of the Container Instance
(which is where the ECS Agent listens).

### Usage
The agent is designed to be run in a container using host network mode. It will also need access to a volume
that maps to the docker socket (`/var/run/docker.sock`). See this docker run command for example:


```
docker run -d -v /var/run/docker.sock:/var/run/docker.sock --name="ecs_id_mapper_agent" --restart="always" --memory="64m" --net=host -e "endpoint=http://<ecs_id_mapper_server>" <image_name>
```
