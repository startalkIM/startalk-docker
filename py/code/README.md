#### ***搜索系统***
--------------------------------------------------------------------------------
#### **准备**：
#### *前提*:
        openssl version >= 1.02
        python3.7及以上 
                https://www.python.org/downloads/source/ 选择最新tar包并下载
                tar -zxvf Python-3.8.1.tgz
                cd Python-3.8.1
                ./configure
                sudo make && make install
        pip
                sudo yum -y install python-pip
        外网接口/nginx等转发服务
        postgresql 10，相关字段参考qtalk
        所需模块见requirements.txt， 建议使用virtualenv部署模块所需环境
                sudo pip install -U virtualenv （安装virtualenv）
                sudo pip install --upgrade pip
                virtualenv --system-site-packages -p python3.8 ./venv （在当前目录下创建venv环境）
                启动环境
                source venv/bin/activate

#### *安装：*:
        1)配置conf/configure.ini
        2)pip install -r requirements.txt （推荐新建虚拟环境）
        3)export PYTHONPATH=path/to/project/qtalk_search:$PYTHONPATH
        4)cd path/to/project/qtalk_search
        5)unlink /tmp/supervisor.sock
        5)supervisord -c conf/supervisor.conf
        7)supervisorctl -c conf/supervisor.conf reload
       
#### *确认服务开启：*:
        确保日志无报错
        tail -f log/access.log

        
--------------------------------------------------------------------------------
#### **请求**
#### *POST( application/json )*:
#### **传参**:
        {
            "key":"he",
            "qtalkId":"jingyu.he",
            "cKey":"xxxxxxmyckey",
            "action":"",
            "start":0,
            "length":10
        }
            *大小写重要, 都是string

            key     :  搜索关键字
            qtalkId :  搜索人userid@domain
            cKey    :  xxxxxxxx ckey规则
            action :  63:all 32:file 24:history 6:group 1:user //二进制111111 搜文件 搜群聊 搜单聊 共同群组 群组 用户 搜哪个哪个就个位就是1
            start   :  偏移量
            length  :  长度
#### **返回**:
        application / json
        {
            "data": [
                {
                    "defaultportrait": "default_single_avatar_url.png",
                    "groupId": "Q01",
                    "groupLabel": "联系人列表",
                    "groupPriority": 0,
                    "hasMore": true,
                    "info": [
                        {
                            "content": "/dep1/dep2",
                            "icon": "aaa.jpg",
                            "label": "个人签名",
                            "name": "张三",
                            "qtalkname": "gtouchgogo",
                            "uri": "gtouchgogo@domain"
                        }
                    ],
                    "todoType": 0
                },
                {
                    "defaultportrait": "default_avatar_url.png",
                    "groupId": "Q02",
                    "groupLabel": "群组列表",
                    "groupPriority": 0,
                    "hasMore": false,
                    "info": [
                        {
                            "content": "群公告",
                            "icon": "bbb.png",
                            "label": "张三,李四",
                            "uri": "weffijw328f2@conference.domain"
                        }
                    ],
                    "todoType": 1
                },
                {
                    "defaultportrait": "default_avatar_url.png",
                    "groupId": "Q07",
                    "groupLabel": "共同群组",
                    "groupPriority": 0,
                    "hasMore": false,
                    "info": [
                        {
                            "content": "群公告",
                            "icon": "bbb.png",
                            "label": "张三,李四",
                            "uri": "weffijw328f2@conference.domain"
                        }
                    ],
                    "todoType": 1
                }
            ],
            "errcode": 0,
            "msg": ""
        }<br />
--------------------------------------------------------------------------------
#### **其它**:
#### *配置文件*:(search/conf/configure.ini)<br />
#### *日志配置文件*:(search/utils/logger_conf.py)<br />
#### *日志文件*:(search/log/yyyy_mm_dd_{module}.log)<br />
        为了避免日志过于冗长，日志会打印当前请求用户的userid+ckey并且打印上一个ip的最后一次请求
