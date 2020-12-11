## What is Startalk-docker?
Startalk is an open source IM platform. It supports all the platforms and OSs you can think of, excellent performance.
Its performance and stability have been proved in Qunar's production during the last ten years.
For more details about Startalk, see: [Startalk Introduction](https://github.com/startalkIM/Startalk/blob/master/README-en.md)  

Although it is very versatile, it's a huge system. We hope the deployement could be more accessible for people who want to try it so that we containerize each module into Docker. Within Docker, it take less than 5 minutes to start it up.

As for usage in production enviroment, the origin way of deployment is more recommended. We have thorough introduction to tell you how to deploy Startalk on CentOS / Ubuntu step by step, even newbie can complete the deployment within a few hours.


## How to get started?
1. Make sure you have docker installed in your system. It is best recommended under
  * Docker version 20.10.0
  * Docker-compose version 1.27.4
  * Dockerfile version 3
  

2. ```git clone git@github.com:startalkIM/startalk-docker.git```  
  It contains docker compose part and source part which have Dockerfile and code for each image in case you want to make some modifications.

3. ```./startalkdockerctl init```

  **WARNING: For users in Windows, if you don't have sed command installed on your PC, we recommend install Git Bash (https://gitforwindows.org/) and then execute this script.**
    
  This script use sed command to correct IP in config files so that Startalk clients can reach the server. It also supports clean up the data and start docker-compose. See startalkdockerctl help. 

4. ```./startalkdockerctl start```

  This equals  docker-compose -d, it starts Startalk in background. 

5. Use PC client connect to the startalk-docker via navigation: http://${ip_you_provide}:8080/newapi/nck/qtalk_nav.qunar  
  Download PC clientfrom our website: [Download Page](https://i.startalk.im/home/#/download)  


## Port Usage:
>  8080 - Openresty  
>  5432 - PostgreSQL  
>  6379 - Redis  
>  5202, 5280, 10050 - Ejabberd  
>  8081 - im_http_service  
>  8082 - qfproxy  
>  8083 - push_service  
>  8884 - search  
  
  Documentation and source code of each service could be found at [Github](https://github.com/startalkIM)    

## Directory structure:

<pre>
├── compose                           # docker compose part.  
│   ├── conf                              # config files for each service.  
│   │   ├── ejabberd  
│   │   ├── im_http_service  
│   │   ├── or  
│   │   ├── push_service  
│   │   ├── qfproxy  
│   │   ├── redis  
│   │   └── search  
│   └── volume                            # volumes, docker mechanism for persisting data.  
│       ├── data                              # database and chat files.  
│       └── log                               # logs for each service.  
├── erl                               # Dockerfile and source code for each image.  
├── java  
│   ├── im_http_service  
│   ├── push_service  
│   └── qfproxy  
├── or  
├── postgresql  
└── py  
</pre>

## Q&A  
  Any questions and suggestions can be through github issue, Email.  
  Github issue: [issue](https://github.com/startalkIM/startalk-docker/issues)  
  Email: app@startalk.im

