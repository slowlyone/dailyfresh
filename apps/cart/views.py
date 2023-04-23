from django.shortcuts import render
from django.views.generic import  View
from  django.http import  JsonResponse

from  goods.models import GoodsSKU
from  django_redis import get_redis_connection
from  utils.mixin import LoginRequireMixin
# Create your views here.

class  CartAddView(View):

    def post(self,request):
        #购物车记录添加
        user= request.user
        if not user.is_authenticated():
            #用户未登录
            return JsonResponse({'res':0,'errmsg':'请登录'})

        sku_id =request.POST.get('sku_id')

        count = request.POST.get('count')

        #数据校验
        if not all([sku_id,count]):
            #返回一个Json的数据
            return JsonResponse({'res':1,'errmsg':'数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            return  JsonResponse({'res':2,'errmsg':'商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return  JsonResponse({'res':3,'errmsg':'商品不存在'})

        #业务处理：添加购物车记录
            #先尝试获取 sku_id 的值
        conn = get_redis_connection('default')
        cart_key ='cart_%d'%user.id
            #先舱室获取 sku_id的值-->  hget (cart_key, 属性)
        cart_count =conn.hget(cart_key,sku_id)    #若sku_id查不到,返回None
        if cart_count:
             count += int(cart_count)


        #校验商品的库存
        if count > sku.stock:
            return  JsonResponse({'res':4,'message':'库存不足'})

        #设置hash 中sku_id 中的值
        conn.hset(cart_key,sku_id,count)   #hset存在更新、不存在新增

        total_count =conn.hlen(cart_key)

        #返回应答
        return  JsonResponse({'res':5,'total_count':total_count,'message':'添加成功'})


class CartInfoView(LoginRequireMixin,View):
    #购物车页面显示
    def get(self,request):
        #显示
        user= request.user   #登录的用户
         #获取用户购物车中的商品的信息
        conn = get_redis_connection('default')
        cart_key ='cart_%d'%user.id
        #{'商品id':'商品数量'}
        cart_dict=conn.hgetall(cart_key)

        skus =[]
        total_count =0  #保存总数量
        total_price =0  #保存总价格
        #遍历获取商品的信息
        for sku_id,count in cart_dict.items():
            #根据商品id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            #计算商品的小计
            amount=sku.price * int(count)
            #动态给sku对象增加一个属性 amount 保存商品的小计
            sku.amount= amount
             #动态给sku对象增加一个属性 count 保存购物车中对应的商品的数量
            sku.count = count
            #添加
            skus.append(sku)

            #累加计算
            total_count += int(count)
            total_price += amount

        #组织上下文
        context =  { 'total_count':total_count,
                     'total_price':total_price,
                     'skus':skus
        }

        return  render(request,'cart.html',context)

#更新购物车记录
#采用ajax post请求。
#前端需要传递的参数： 商品id(sku_id) 更新的商品数量(count)
#/cart/update
class CartUpdateView(View):
    #购物车记录更新
    def post(self,request):

        user= request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请登录'})
        #接收数据
        sku_id =request.POST.get('sku_id')
        count = request.POST.get('count')
        #数据校验
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据不完整'})
        try:
            count = int(count)
        except Exception as e:
            return  JsonResponse({'res':2,'errmsg':'商品数目出错'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return  JsonResponse({'res':3,'errmsg':'商品不存在'})

        #业务处理： 更新购物车记录
        conn = get_redis_connection('default')
        cart_key='cart_%d'%user.id
            #校验商品的库存
        if count >sku.stock:
            return  JsonResponse({'res':4,'errmsg':'商品库存不足'})

        conn.hset(cart_key,sku_id,count)  #更新

        total_count =0
        #技术用户购物车商品的总件数。  {‘1’：5，‘2’：3}
            #hvals() 取一个哈希里面的所有value 值
        vals=conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return  JsonResponse({'res':5,'total_count':total_count,'message':'更新成功'})


#删除购物车记录
#采用ajax post请求
#前端需要传递参数：是商品的id（sku_id)
#/cart/delete
class CartDeleteView(View):

    def post(self,request):

        user =request.user
        if not user.is_authenticated():
            return  JsonResponse({'res':0,'errmsg':'请先登录'})

        #接受参数
        sku_id =request.POST.get('sku_id')

        #数据校验
        if not sku_id:
            return  JsonResponse({'res':1,'errmsg':'无效的商品id'})

        #校验商品是否存在
        try:
            sku =GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return  JsonResponse({'res':2,'errmsg':'商品不存在'})

        #业务处理：删除购物车记录
        conn = get_redis_connection('default')
        cart_key ='cart_%d'%user.id
        conn.hdel(cart_key,sku_id)


        total_count =0
        #计算用户购物车商品的总件数。  {‘1’：5，‘2’：3}
        #hvals() 取一个哈希里面的所有value 值
        vals=conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res':3,'total_count':total_count,'message':'删除成功'})






