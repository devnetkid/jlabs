# JLabs

* [Initial setup](#initial-setup)
* [Workflow for creating a toml file from an existing lab](#workflow-for-creating-a-toml-file-from-an-existing-lab)
* [Workflow for loading a lab](#workflow-for-loading-a-lab)

## Initial setup

Your Eve-NG server IP address is required. Define an environment variable called JLABS_EVENG_IP.
- Example: `export JLABS_EVENG_IP="192.168.1.1"`

When you run the script for the first time it will create a folder in your home directory called jlabs. In this folder will be two more folders, one for labs and the other for logs.

The default log level is info. To change it simply add an environment variable called JLABS_LOG_LEVEL.
- Example: `export JLABS_LOG_LEVEL="debug"`


## Workflow for creating a toml file from an existing lab

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

## Workflow for loading a lab

Make sure to first add a lab and configs. Create a folder inside your ~/jlabs/labs directory and folder called configs inside that one.

```
.
└── basic-two-router
    ├── configs
    │   ├── r1.cfg
    │   └── r2.cfg
    └── lab.toml
```

Now to load up this lab we will launch jlabs script and select the **Labs** option from the **Main Menu**.

<img width="411" height="290" alt="Screenshot 2026-05-22 at 1 55 28 PM" src="https://github.com/user-attachments/assets/7422f016-af36-460e-8892-3537e5dff404" />

Next, we want to choose to **Load a lab**.

<img width="521" height="335" alt="Screenshot 2026-05-22 at 1 57 49 PM" src="https://github.com/user-attachments/assets/ba1e8a36-1b94-4750-961a-d20a387b479f" />

A list of all the folders in your labs folder will appear as options for labs to load.

<img width="721" height="353" alt="Screenshot 2026-05-22 at 2 00 21 PM" src="https://github.com/user-attachments/assets/c85b61e7-9ecd-42af-a7bc-1b5204167c48" />

Once you make a choice on this menu it will attempt to create your lab according to the lab.toml file.

> [!note]
> Once you are done with said lab, you will want to shut it down. This properly stops running nodes, closes and deletes the lab from Eve-NG, as well as removing a state file.

> [!note]
> If you want to start over or are using the same topology for another lab, you can just select **Restart lab with base configs**

