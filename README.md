# JLabs

## Initial setup

Your Eve-NG server IP address is required. Define an environment variable called JLABS_EVENG_IP.
- Example: `export JLABS_EVENG_IP="192.168.1.1"`

When you run the script for the first time it will create a folder in your home directory called jlabs. In this folder will be two more folders, one for labs and the other for logs.

The default log level is info. To change it simply add an environment variable called JLABS_LOG_LEVEL.
- Example: `export JLABS_LOG_LEVEL="debug"`


## Workflow for creating a lab.toml file from an existing lab build in Eve-NG

JLabs uses a TOML file format to build a lab inside Eve_NG. You can edit it by hand but you can also build a lab topology in Eve-NG and convert it to a TOML file. To do this select Tools from the Main Menu then Create a lab file from an existing lab in the Tools Menu. You will be prompted for the name of the lab en Eve-NG. The result will be a file in your ~/jlabs/labs directory. 

The example below came from a lab where I added two routers with a cable between them on their Gi0/0 interfaces.

## Example TOML file - lab.toml

```
[lab]
author = ""
description = ""
body = ""
name = "2r_temp"
version = "1"
scripttimeout = 300
path = "/"

[[nodes]]
console = "telnet"
delay = 0
id = 1
left = 576
icon = "Router.png"
image = "vios-adventerprisek9-m.SPA.157-3.M3"
name = "r1"
ram = 1024
status = 0
template = "vios"
type = "qemu"
top = 210
cpu = 1
ethernet = 4

[[nodes]]
console = "telnet"
delay = 0
id = 2
left = 747
icon = "Router.png"
image = "vios-adventerprisek9-m.SPA.157-3.M3"
name = "r2"
ram = 1024
status = 0
template = "vios"
type = "qemu"
top = 210
cpu = 1
ethernet = 4

[[cables]]
type = "ethernet"
source = "r2"
source_type = "node"
source_label = "Gi0/0"
destination = "r1"
destination_type = "node"
destination_label = "Gi0/0"
```


