from  django.core.files.storage import Storage
from  fdfs_client.client import Fdfs_client,get_tracker_conf
from  django.conf import settings

class FDFSStorage(Storage):
    #fas dfs文件存储类
    def __init__(self,client_conf=None,base_url=None):
        #初始化的传参。为了下面的路径不写死
        if client_conf is None:
            client_conf=settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url =settings.FDFS_URL

        self.base_url =base_url

    def _open(self,name,mode='rd'):
        #打开文件时使用     【这里不涉及到打开
        pass

    def _save(self,name,content):
        '''     #保存文件时使用 。点击文件上传的时候调用save方法，两个参数
        :param name: 选择上传文件的名字
        :param content: 包含你上传文件内容的file对象,。。以获取文件的内容

        :return: res是下面的格式
             dict {
            'Group name'      : group_name,
            'Remote file_id'  : remote_file_id,
            'Status'          : 'Upload successed.',
            'Local file name' : '',
            'Uploaded size'   : upload_size,
            'Storage IP'      : storage_ip
        } if success else None
        '''

        #创建一个Fdfs_client对象
        # client=Fdfs_client(self.client_conf)    老掉牙版本
        tracker_path=get_tracker_conf(self.client_conf)
        client = Fdfs_client( tracker_path)

        try:
        #上传文件到fast dfs 系统中
            res =client.upload_by_buffer(content.read()) #根据文件的内容[conetnt.read()获取]   去上传文件
            print('XXX')
        # XXXX
            print(res)
        except:
           print('上传文件有误  ')

        if res.get('Status') != 'Upload successed.':
            #上传失败
            raise Exception('上传文件到fastdfs失败')


         #获取返回的文件ID
        filename = res.get('Remote file_id')
        print('XXXfilename')
        print(filename)
        # return  filename  #老版本 是返回字符串
        return  filename.decode()

    def exists(self, name):
        '''
         #django在条用save()之前，会先exists()方法，目的：判断django服务器的文件名是否可用
         如果name已经存在，返回True,如果这个名称可用于新文件返回False
        :param name:
        :return: 由于django不存储图片，所以拥有返回False,直接保存到FastDFS
        '''
        return  False


    def url(self,name ):
        '''
        如果你点击 你上传的图片的时候-需要显示、则你需要定义url函数。返回访问文件的url路径。

        :param name: 是django传过来的name,上面的filename
        就是group1/M11/00XXXX  url后面的地址值，即文件id
        :return:
        '''
        print('XXX')
        print(name)
        # return 'www.baidu.com'
        return self.base_url +name

