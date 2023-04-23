from django.shortcuts import render,redirect
from django.core.urlresolvers import  reverse
from user.models import  User,Address
from  goods.models import  GoodsSKU
import  re
from  django.http import  HttpResponse
from  django.views.generic import View   #类视图

from utils.mixin import LoginRequireMixin

from  django.contrib.auth import authenticate,login,logout
# from  celery_tasks.tasks import send_register_active_email
from itsdangerous import  TimedJSONWebSignatureSerializer as Serialzer
from  itsdangerous import SignatureExpired
from  django.conf import  settings

from goods.models import  OrderInfo,OrderGoods
# from django.core.mail import  send_mail
# Create your views here.

from  django_redis import  get_redis_connection
from  django.core.paginator import Paginator

def register(request):   #传统写法 记忆忽略
    ''' 显示注册页面
    :param request:  通过请求方式不一样get、post。显示注册和注册处理 在东一个view函数里面。
        而不用拆成两个 函数。
    :return:
    '''
    if request.method=='GET':  #显示注册页面
        return  render(request,'register.html')
    else:#注册处理
        user_name=request.POST.get('user_name')
        password=request.POST.get('pwd')
        email=request.POST.get('email')
        sure_password = request.POST.get('cpwd')
        allow = request.POST.get('allow')

        #进行数据校验  1、判断三个参数是不是都传了  2、判断邮箱合法  3、两次密码一致 4、判断用户是否同意这个协议
        if not all([user_name,password,email]):  #all(迭代对象)，判断迭代对象里面是不是都为真
            return render(request,'register.html',{'errmsg':'数据不完整'}) #有空返回一个，信息提示

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return  render(request,'register.html',{'errmsg':'邮箱不正确'})

        if sure_password != password:
            return  render(request,'register.html',{'errmsg':'两次密码不一致'})

        if allow !='on':  #前端勾选，会返回一个on
            return  render(request,'register.html',{'errmsg':'请同意协议'})

        try:  #校验用户名是否重复。查找
            user =User.objects.get(username=user_name)
        except  User.DoesNotExist:   #检查这个异常
            #如果抛这个异常的话，说明用户名是不存在的。说明这个用户可以插入数据库
            user=None
        if user:
            return  render(request,'register.html',{'errmsg':'用户名已存在'})

        #进行业务处理： 进行用户注册。
        #正常来说：# user =User()# user.username = user_name# user.password= password# user.save()
            #使用django的认证系统：有create_user()函数，--[除了添加数据；还有用户名重复的话，会报异常]
        user =User.objects.create_user(user_name,email,password)


        user.is_active = 0   #单独 设置 ‘没激活’字段为0
        user.save()


        #返回应答,
        return redirect(reverse('goods:index'))   #reverse:是反向解析的作用。[全局goods里]


class  RegisterView(View):
    '''注册 类试图 知识'''
    def get(self,request):  #类视图中，get函数【名字固定】,处理get请求
        return  render(request,'register.html')
    def  post(self,request):
        user_name=request.POST.get('user_name')
        password=request.POST.get('pwd')
        email=request.POST.get('email')
        sure_password = request.POST.get('cpwd')
        allow = request.POST.get('allow')

        if not all([user_name,password,email]):  #all(迭代对象)，判断迭代对象里面是不是都为真
            return render(request,'register.html',{'errmsg':'数据不完整'}) #有空返回一个，信息提示

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return  render(request,'register.html',{'errmsg':'邮箱不正确'})

        if sure_password != password:
            return  render(request,'register.html',{'errmsg':'两次密码不一致'})

        if allow !='on':  #前端勾选，会返回一个on
            return  render(request,'register.html',{'errmsg':'请同意协议'})

        try:
            user =User.objects.get(username=user_name)
        except  User.DoesNotExist:
            user=None
        if user:
            return  render(request,'register.html',{'errmsg':'用户名已存在'})

        user =User.objects.create_user(user_name,email,password)
        # user.is_active = 0 这里不适应邮箱认证了，直接设置为1，代表激活
        user.is_active = 1

        user.save()

        #发送激活邮件，包含激活链接：
       # 【1 激活链接中，需要包含用户的身份信息()；】故连接 /user/active/1 是id。
       #【并且将id身份信息进行加密处理，】

        serializer=Serialzer(settings.SECRET_KEY,3600)  #加密用户的身份信息=即生成激活的token
        info = {'confirm':user.id }
        token =serializer.dumps(info)

        #celery 发邮件 , 里面的delay()函数 可以放入任务队列。
        # send_register_active_email.delay(email,user_name,token)

        return redirect(reverse('goods:index')) #reverse是反向解析的意思 。到首页


#3 定义对应链接，即激活的视图，，用户邮箱收到的链接。
class ActiveView(View):
        ''' 用户激活
        '''
        def  get(self,request,token):
            ''' 进行用户激活
            '''
            #解密，获取要激活的用户信息
            serializer= Serialzer(settings.SECRET_KEY,3600)
            try:
                info=serializer.loads(token)   #info是解密的信息

            except SignatureExpired as e:
                #激活链接已过期
                return  HttpResponse('激活链接已过期')

            user_id = info['confirm']
            user= User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            #跳转到用户页面
            return  redirect(reverse('user:login'))

#/user/login
class LoginView(View):
    '''登录'''
    def get(self,request):
        ''' 显示登录页面'''
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked='checked'   #模板里面 如果是checked ,那复选框就会被选中
        else:
            username=""
            checked=""
        return  render(request,'login.html',{'username':username,'checked':checked})

    def post(self,request):
        '''登录检验 '''
        username =request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username,password]):
            return  render(request,'login.html',{'errmsg':'数据不完整'})

        #登录检验。 使用django内置的认证系统
        # User.objects.get(username=username,password=password) 正常来说是查找数据库,可数据库密码是加密的

        user =authenticate(username=username,password=password)
        if user is not  None:  #用户名和密码正确
            if user.is_active: #代表激活
                login(request,user)
                # (登录装饰器课程)获取登录后所要跳转的地址   /user/login/?next=/user/
                next_url = request.GET.get('next',reverse('goods:index')) #get()可以指定默认值，当查找不到的时候
                    #默认跳转到首页
                response = redirect(next_url)


                remember = request.POST.get('remember')
                if remember == 'on':
                    #将用户名放到cookies里面
                    response.set_cookie('username',username,max_age=2*3600)
                else:
                    response.delete_cookie('username')

                return response


            else:
                return  render(request,'login.html',{'errmsg':'账户未激活'})
        else:
            # print('the username and paw were incorrcet')
            return  render(request,'login.html',{'errmsg':'用户名和密码错误'})


class LogoutView(View):
    '''#用户退出'''
    def get(self,request):
        ''' 推出登录'''
        #清楚用户的session信息
        logout(request)
        #跳转到首页
        return  redirect(reverse('goods:index'))


# /user
class  UserInfoView(LoginRequireMixin,View):
    ''' 用户中心-信息页'''
    def get(self,request):
        # request.user.is_authenticated() 除了你给模板文件传递的模板变量之外，
        # django框架会把request.user也传给模板文件。

        #获取用户个人信息
        user = request.user
        address= Address.objects.get_default_address(user)

        #获取用户的历史浏览记录
        # from  redis import  StrictRedis  #第一种方式
        # sr =StrictRedis(host='192.168.1.112',port=6379,db=9) #链接redis数据库
        con = get_redis_connection('default')

        history_key='history_%d'%user.id
         #获取用户最新浏览的5个商品的id
        sku_ids=con.lrange(history_key,0,4)  #获取前5个，即最近浏览的5个商品id  。[空的]

        #从数据库中查询用户浏览的商品的具体信息
        goods_res=[]
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_res.append(goods)

        content={'page':'user','address':address,'goods_li':goods_res}

        return  render(request,'user_center_info.html',content)




# user/order
class  UserOrderView(LoginRequireMixin,View):
    ''' 用户中心-订单页'''
    def get(self,request,page):
        #获取用户订单信息
        user = request.user
        orders=OrderInfo.objects.filter(user=user).order_by('-create_time')  #一个订单集合
        #便利获取订单商品的信息
        for order in orders:
             #根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id = order.order_id)  #得到一个查询集

            #遍历order_skus计算商品的小计
            for order_sku in  order_skus:
                #计算小计
                amount =order_sku.count * order_sku.price
                #动态 给order_sku增加属性 amount,b保存订单商品的小计
                order_sku.amount = amount

            #动态给order增加属性，保存订单状态标题。
            order.order_status=OrderInfo.ORDER_STATUS[order.order_status]
            #动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        #进行分页  //对orders进行分页 ,每一页显示1条
        paginator = Paginator(orders,1)
            #处理页码 。 和goods/views里面一样
        try:
            page= int(page)
        except:
            page=1

        if page > paginator.num_pages: #大于总页数
            page=1

        #获取第page页的Page实例对象
        order_page = paginator.page(page)

        num_pages= paginator.num_pages
        if num_pages <5:
            pages = range(1,num_pages+1)
        elif page <=3:
            pages = range(1,6)

        elif num_pages - page <=2:
            pages = range(num_pages-4,num_pages+1)

        else:
            pages = range(page-2,page+3)

        #组织上下文
        context = {'order_page':order_page,'pages':pages,}
        return  render(request,'user_center_order.html',context)


# user/address
class  AddressView(LoginRequireMixin ,View):
    ''' 用户中心-地址页'''
    def get(self,request):
        #获取用户的默认收获地址
        user = request.user
        # try:
        #     address =Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:#不存在默认的收获地址
        #     address=None
        address=Address.objects.get_default_address(user)

        return  render(request,'user_center_site.html',{'page':'address','address':address})

    def post(self,request):
        #地址的添加
        receiver=request.POST.get('receiver')   #接受数据
        addr=request.POST.get('addr')
        zip_code=request.POST.get('zip_code')  #邮编，在数据定义的时候是允许为空
        phone=request.POST.get('phone')

            #校验数据
        if not all([receiver,addr,phone]):
            return  render(request,'user_center_site.html',{'errmsg':'数据不完整'})

            #业务处理
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return  render(request,'user_center_site.html',{'errmsg':'手机不合法'})
            #2地址添加: 如果用户已存在默认收获地址，添加的地址不作为默认收获地址，否则
        user = request.user  #获取登录用户对应的user对象
        # try:
        #     address =Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:#不存在默认的收获地址
        #     address=None
        address=Address.objects.get_default_address(user)

        if address:
            is_default=False
        else:         #不存在默认地址，就将第一次作为默认地址。
            is_default=True
        #添加信息
        Address.objects.create(user=user,receiver=receiver,
                               addr=addr,zip_code=zip_code
                               ,phone=phone,is_default=is_default)
            #返回应答 --刷新地址页面
        return  redirect(reverse('user:address')) #重定向是 get请求方式，所以写get函数
