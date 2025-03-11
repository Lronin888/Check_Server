from openai import OpenAI
import time
import os
from dotenv import load_dotenv
from ollama import Client
import paramiko
from concurrent.futures import ThreadPoolExecutor


#巡检命令列表
commands = [
    "uname -a", "hostname", "cat /etc/os-release", "lsb_release -a", "uptime",
    "lspci", "lsusb", "lsblk",
    "ss -tunlp", "ip addr",
    "df -Th",  "lsblk", "mount",
    "last", "who", "cat /etc/passwd", "cat /etc/sudoers","iptables -nvL", "firewalld --list-all",
    "ps aux", "systemctl list-units --type=service --no-pager",
    "crontab -l", "date", "timedatectl",
    "top -bc -o %MEM | head -n 17|sed -n '7,17p'", "top -bc -o %CPU | head -n 17|sed -n '7,17p'",
    "du -h --exclude=/proc --exclude=/sys / | sort -rh | head -n 20",

]

def AI_V3(data,ipadd,api_key):
  client = OpenAI(
      base_url='https://ark.cn-beijing.volces.com/api/v3',
      api_key=api_key,

  )
  prompt = '''
      你是一名拥有 RHCE/CCIE/HCIE/H3CSE 认证的高级工程师，擅长解析Linux服务器配置，能够根据用户提供的配置信息完成以下任务：
      1.识别配置类型：区分Linux发行版（如CentOS/Ubuntu）配置。
      2.解析关键参数：包括系统服务、防火墙安全策略、存储配置、网络参数、日志监控等。
      3.检测潜在问题：权限漏洞、服务风险、配置冲突、性能瓶颈、安全隐患等。
      4.生成结构化报告：提供优化建议和修复方案，支持Markdown格式。
      明白你的身份回复1
  '''


  stream = client.chat.completions.create(

      model="ep-m-20250228165213-cct67",
      messages=[
          {"role": "system", "content": prompt},
          {"role": "user", "content": data},
      ],

      stream=True,
  )
  filename = f'{dir_url}\%s' % ipadd + '.md'
  for chunk in stream:
      if not chunk.choices:
          continue
      print(chunk.choices[0].delta.content, end="",
      file=open(f'{filename}','a'))
  return filename

#调用本地大模型处理
def local_ollama(data,ipadd):
    client = Client(host='http://localhost:11434')
    text= '''
      你是一名拥有 RHCE/CCIE/HCIE/H3CSE 认证的高级工程师，擅长解析Linux服务器配置，能够根据用户提供的配置信息完成以下任务：
      1.识别配置类型：区分Linux发行版（如CentOS/Ubuntu）配置。
      2.解析关键参数：包括系统服务、防火墙安全策略、存储配置、网络参数、日志监控等。
      3.检测潜在问题：权限漏洞、服务风险、配置冲突、性能瓶颈、安全隐患等。
      4.生成结构化报告：提供优化建议和修复方案，支持Markdown格式。
      明白你的身份回复1
  '''

    response_stream = client.generate(
        model='qwen:1.8b',
        system=text,
        prompt=data,
        options={
            'temperature': 1,
        },
        stream=True 
    )
    try:
        filename = f'{dir_url}\%s' % ipadd + '.md'
        for chunk in response_stream:

            print(chunk['response'], end='',flush=True,
            file=open(f'{filename}', 'a'))
            time.sleep(0.02) 
        return filename
    except KeyboardInterrupt:
        print("\n用户中断了生成")
    except Exception as e:
        print(f"\n生成异常: {str(e)}")

def inspect_server(ip_address,user,passwd,port):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ip_address, port=port, username=user, password=passwd)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{dir_url}\inspection_server_{ip_address}_{timestamp}.txt"
        with open(filename, 'w') as report:
            report.write(f"=== 服务器巡检报告 - {ip_address} ===\n")
            report.write(f"巡检时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            results = []
            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                output = stdout.read().decode("utf-8").strip()
                report.write(f"{cmd}:\n{output}\n\n")
                report.write("-"*60 + "\n")
                report.write(output + "\n\n")
                print(f"{ip_address} 成功执行 {cmd}")
                error = stderr.read().decode("utf-8").strip()
                if error:
                    results.append(f"Error on {ip_address}: {error}")
                else:
                    results.append(f"Output from {ip_address}:\n{output}")
        client.close()
        return filename
    except Exception as e:
        return f"Failed to connect to: {str(e)}"


def main():
    global dir_url
    dir_url = r"D:\server"
    load_dotenv(r'D:\server\.env')
    devices = [f'192.168.10.{ip}' for ip in range(32, 34)]
    port=os.getenv("PORT")
    user=os.getenv("USER")
    passwd=os.getenv("PASSWORD")
    api_key=os.getenv("HS_API_KEY")

    for ip in devices:
        print(f"\n开始巡检设备 {ip}")
        report_file = inspect_server(ip,user,passwd,port)
        time.sleep(1)
        with open(f'{report_file}','r') as f:
            check_file = f.read()
            Report = AI_V3(check_file, ip,api_key)
            #Report = local_ollama(check_file, ip)
            time.sleep(2)
            if report_file:
                print(f"巡检报告已生成：{Report}")
        os.remove(report_file)
        print("-"*60)

if __name__ == '__main__':
    main()
