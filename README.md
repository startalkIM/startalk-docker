##
### 文件结构
- images  
  镜像文件
- Dockfile  
  Dockerfile
- permfile.zip  
  持久性文件，包括db数据、服务日志数据、redis数据、聊天上传的文件

````
安装步骤
1、获取资源文件 wget http://150.242.184.16/startalk_docker.zip 并解压
2、解压permfile.zip: unzip -x permfile.zip
3、load 镜像: docker load < startalk_docker/images/startalk_docker.tar
4、创建volume docker volume create startalkpgdata
4、查看镜像id: docker images
5、启动镜像
docker run  -v startalk_docker/permfile:/startalk/permfile -v startalkpgdata:/startalk/data -p 8080:8080 -p 5202:5202 -e hosturl="机器ip"  镜像id(可由第4步或得)
6、需要注意的点: 
 1.-v 后面接的是持久性文件在宿主机上的绝对路径，如您将permfile.zip 解压到了 /home/startalk/permfile 则-v /startalk/permfile:/startalk/permfile.冒号后面的路径不需改动  
 2.-p 配置了宿主机与container的端口映射。如上述 需要用到宿主机暴露两个端口8080 5202
 3.hosturl 是宿主机的ip，作为参数传给container,如果您配置的是内网ip 那整套IM 只能在内网使用，如果您配置的是公网ip 则外网也可以使用 
 4.docker 版本：build image 是用的 Docker version 18.09.2，避免因为版本问题，建议使用>=18.09

````
###  
安装成功后后会提示如下字样:  
![image](success.png)  
下载客户端配置导航即可登录

````
常用docker 指令
1、查看当前运行容器 docker ps
2、查看所有容器 docker ps -a
3、查看加载的镜像 docker images
4、停止容器 docker stop {容器ID} 例子：docker stop dfb01d665700
5、进入容器内部 docker exec -it {容器ID} /bin/bash 例子：docker exec -it dfb01d665700 /bin/bash

````
