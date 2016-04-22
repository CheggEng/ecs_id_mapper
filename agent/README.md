## ECS ID Mapper Agent

The agent runs on the ECS Container Instance and queries the ECS agent and the EC2 Metadata services for information. 
The container needs to run in host networking mode so it can access the loopback interface of the Container Instance 
(which is where the ECS Agent listens).