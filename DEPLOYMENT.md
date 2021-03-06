# 部署说明

- 部署目录 = DEPLOYDIR
- 部署用户 = USER
- 部署端口 = PORT
- Python3可执行文件目录 = PYBIN
- 日志文件地址 = SERVELOG, CRONLOG

## 部署代码

```bash
mkdir -p DEPLOYDIR
git clone https://github.com/observerss/ybk DEPLOYDIR
cd DEPLOYDIR
python3 setup.py develop

# 验证安装完毕
ybk --help

# 修改配置文件(也可以直接用命令行参数给)
cp config.yaml.default config.yaml
vim config.yaml
```


## 运行

### Server

直接执行

```bash
ybk serve --production --mongodb_url=mongodb://localhost/ybk --num_processes=4 --port=PORT --secret_key=ybk369
```

或者用supervisor来起这个服务

```bash
; /etc/supervisor/conf.d/ybk369.conf 

[program:ybk369]
command=PYBIN/ybk serve --production --port=5001 --num_processes=2 --secret_key=ybk369
stdout_logfile=SERVELOG
directory=DEPLOYDIR
user=USER
autostart=true
autorestart=true
startretries=30
redirect_stderr=True
```

```bash
sudo apt-get install supervisor
mkdir -p DEPLOYDIR/log
sudo supervisorctl start ybk369
```


设置Nginx转发

```bash
# /etc/nginx/sites-enabled/ybk369.com

server {
    server_name ybk369.com;
    return 301 $scheme://www.ybk369.com$request_uri;
}

server {
    server_name www.ybk369.com;

    location /static/ {
        root DEPLOYDIR/ybk;
        try_files $uri $uri/ /index.html;
    }

    location / {
        proxy_pass http://localhost:PORT;
        include /etc/nginx/proxy_params;
    }
}
```

Nginx with https


```
server {
    listen 80;
    server_name ybk369.com www.ybk369.com;
    return 301 https://www.ybk369.com$request_uri;
}

server {
    listen 443 ssl;
    server_name www.ybk369.com;

    ssl_certificate /etc/nginx/cert.d/www.ybk369.com.crt;
    ssl_certificate_key /etc/nginx/cert.d/www.ybk369.com.key;


    location /static/ {
        root /var/www/ybk369.com/ybk;
        try_files $uri $uri/ /index.html;
    }

    location / {
        proxy_pass          http://localhost:5001;
        include             /etc/nginx/proxy_params;
    }
}
```

### Cronjob


```bash
# 每5分钟执行一次
*/5 * * * * PYBIN/ybk cron --mongodb_url=mongodb://localhost/ybk >> CRONLOG 2>&1
```
