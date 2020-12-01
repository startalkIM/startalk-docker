#### ***搜索系统***
--------------------------------------------------------------------------------
#### **准备**：
#### *前提*:
        python3 (3以上都可以，以3.6为标准)
                sudo yum install https://centos7.iuscommunity.org/ius-release.rpm
                sudo yum install python36u
        pip
                sudo yum -y install python-pip
        外网接口/nginx等转发服务转发
        postgresql10，相关字段参考qtalk
        所需模块见requirements.txt， 单独部署建议使用virtualenv部署模块所需环境
                sudo pip install -U virtualenv （安装virtualenv）
                sudo pip install --upgrade pip
                virtualenv --system-site-packages -p python3.6 ./venv （在当前目录下创建venv环境）
                启动环境
                source venv/bin/activate

#### *安装：*:
        1)配置conf/configure.ini
        2)pip install -r requirements.txt （推荐新建虚拟环境）
        3)export PYTHONPATH=path/to/project/qtalk_search:$PYTHONPATH
        4)cd path/to/project/qtalk_search
        5)nohup python3.6 search.py &
        6)deactivate(退出环境)
        
--------------------------------------------------------------------------------
#### **请求**
#### *POST( application/json )*:
#### **传参**:
        {
            "key":"he",
            "qtalkId":"jingyu.he",
            "cKey":"xxxxxxmyckey",
            "groupid":"",
            "start":10,
            "length":0
        }
            *大小写重要, 都是string

            key     :  搜索关键字
            qtalkId :  搜索人qtalk id
            cKey    :  xxxxxxxx ckey规则
            groupid :  Q01-Q07 限定搜索内容
            length   :  用于分页长度
            start  :  用于分页起始
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
        }
--------------------------------------------------------------------------------
#### **其它**:
#### *配置文件*:(search/conf/configure.ini)
#### *日志配置文件*:(search/utils/logger_conf.py)
#### *日志文件*:(search/log/{module}.log)
        为了避免日志过于冗长，日志会打印当前请求用户的userid+ckey并且打印上一个ip的最后一次请求
