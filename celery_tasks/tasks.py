#使用celery
from  celery import  Celery

from django.conf import settings
from  django.core.mail import  send_mail
from  django.template import  loader,RequestContext
# from  goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

import  os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","dailyfresh.settings")   #处理者端加载django的配置项目。
django.setup()
from  goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

#创建一个Celery类的实例对象。
app =Celery('celery_tasks.tasks',broker='redis://192.168.1.112:6379/8')  #名字任意，一般使用路径命名 以区分
                #broker:中文中间人意思。指定redies数据库，地址:端口+库名，celery会帮我们链接他。



#定义任务函数
@app.task     #app对象有个task方法 装饰下面的函数
def send_register_active_email(to_email,user_name,token):
    subject ='天天生鲜欢迎你'
    message = ''
    sender=settings.EMAIL_FROM
    receiver= [to_email]

    html_message = '<h1>%s,欢迎你成为天天生鲜注册会员<h1>请点击下面链接激活你的账户<br/>' \
                  '/active/%s/http://127.0.0.1:8000/user/active/%s</a>'%(user_name,token,token)
    send_mail(subject,message,sender,receiver,html_message=html_message)


@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners


    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 使用模板
    # 1.加载模板文件
    temp = loader.get_template('static_index.html') #返回模板对象
    # 2.模板渲染
       #将数据传过去
    static_index_html = temp.render(context)

    #它内容有了，, 生成首页对应静态文件【生成到static里面】
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)
