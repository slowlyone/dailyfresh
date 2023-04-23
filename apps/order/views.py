from django.shortcuts import render,redirect
from  django.views.generic import  View
from  django.core.urlresolvers import reverse
from  django.http import  JsonResponse
from  django.db import  transaction
from  django.conf import  settings

from  user.models import  Address
from  goods.models import  GoodsSKU

from  django_redis import  get_redis_connection
from utils.mixin import LoginRequireMixin
from order.models import  OrderInfo,OrderGoods

from  datetime import  datetime
from  alipay import  AliPay
import  os

# Create your views here.
# /order/place
class OrderPlaceView(LoginRequireMixin,View):
    #提交订单显示页面
    def post(self,request):
        #提交订单显示页面
        user =request.user

        sku_ids=request.POST.getlist('sku_ids')
        #校验参数
        if not sku_ids:
            #跳转到购物车页面
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key ='cart_%d'%user.id

        skus=[]
        total_count = 0
        total_price = 0
        #遍历ksu_ids 获取用户购买的商品信息
        for  sku_id in sku_ids:
            #根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            #获取用户所要购买的商品的数量
            count=conn.hget(cart_key,sku_id)
            #计算商品的小计
            amount = sku.price*int(count)

            #动态给sku增加属性  count, 保存购买商品的数量
            sku.count =count
            #动态给sku增加属性  amount, 保存购买商品的小计
            sku.amount = amount
            skus.append(sku)
            #累加计算商品的总件数和总价格
            total_count +=int(count)
            total_price +=amount

        #运费：实际开发的时候， 属于一个专门计算 运费的子系统
        transit_price = 10 #写死

        #实付款
        total_pay = total_price + transit_price

        #获取用户的收件地址
        addrs=Address.objects.filter(user=user)

        #组织上下文
        sku_ids = ','.join(sku_ids)       #传递给前端，提交订单的a标签里增加一个属性sku_ids，存储用户买了哪些商品
        context = {'skus':skus,
                   'total_count':total_count,
                   'total_price':total_price,
                   'transit_price':transit_price,
                   'total_pay':total_pay,
                   'addrs':addrs,
                   'sku_ids':sku_ids
                   }

        #使用模板
        return  render(request,'place_order.html',context)

#前端传递的参数：地址id(addr_id) 支付方式(),用户要购买的商品id字符串(sku_ids)
class  OrderCommitView(LoginRequireMixin,View):
    #订单创建
    @transaction.atomic
    def post(self,request):
        #订单创建
        user= request.user
        if user.is_authenticated():
            #未登录
            return  JsonResponse({'res':0,'errmsg':'用户未登录'})

        #接受参数
        addr_id = request.POST.get('addr_id')
        pay_method=request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        #校验参数
        if not all([addr_id,pay_method,sku_ids]):
            return  JsonResponse({'res':1,'errmsg':'参数不完整'})

        #校验支付方式
        if pay_method not in  OrderInfo.PAY_METHOD_CHOICES.keys():
            return JsonResponse({'res':2,'errmsg':'非法的支付方式'})

        #校验地址
        try:
            addr= Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            #地址不存在
            return JsonResponse({'res':3,'errmsg':'地址非法'})

        #todo:创建订单核心业务
            #向df_ordere_info表中添加一条记录 。缺
                # 订单order_id: 20171221_用户id 、total_count、total_price、transit_price。
        order_id =datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        #运费
        tranist_price =10
        #总数目和总金额
        total_count =0
        total_price =0

        #设置事务保存点 。可以回滚到这个位置，使得后面的撤销。
        save_id=transaction.savepoint()

        #把涉及到数据库操作的整段
        try:
            #todo:向df_ordere_info表中添加一条记录
            order =OrderInfo.objects.create(order_id=order_id,
                                            user=user,
                                            addr=addr,
                                            pay_method=pay_method,
                                            total_count=total_count,
                                            total_price=total_price,
                                            tranist_price=tranist_price)

            #用户的订单中有几个商品_就需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            sku_ids =sku_ids.split(',')   #[]

            for sku_id in sku_ids:
                #获取商品信息
                try:
                    #select * from df_good_sku where id =17  for update;
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    #回滚到保存点
                    transaction.savepoint_rollback(save_id)

                    #商品不存在
                    return  JsonResponse({'res':4,'errmsg':'商品不存在'})



        #       #从redes 中获取用户所要购买的商品的数量
                count =conn.hget(cart_key,sku_id)

                #todo:判断商品的库存。。[因为如果有两个用户抢单，看谁先提交]
                if int(count) > sku.stock:
                    #回滚到保存点
                    transaction.savepoint_rollback(save_id)

                    return  JsonResponse({'res':6,'errmsg':'商品库存不足'})
                #当库存不足的时候，这个订单是下失败的，后面不应该向表里面插入信息了。


                #向df_order_goods中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                #用户下完了订单，商品的销量、库存要改变。
                #todo:更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                #todo:累加计算 订单商品的总数目和总价格
                amount = sku.price * int(count )
                total_count += int(count)
                total_price += amount

            #循环之后，更新订单信息表中的商品总数量和 总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()

        except Exception as e:  #若对数据库操作异常 -也要回滚到前面的保存点
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7,'errmsg':'下单失败'})

        #提交事务: 【前面都OK无异常之后】
        transaction.savepoint_commit(save_id)

        #清除购物车记录：用户在买完商品之后，它的购物车记录里面的商品需要删除。hdel
        conn.hdel(cart_key,*sku_ids)   #将列表 拆包，传递过去

        #返回应答
        return  JsonResponse({'res':5,'message':'创建成功'})



class  OrderCommitView2(LoginRequireMixin,View):
    #订单创建
    @transaction.atomic
    def post(self,request):
        #订单创建
        user= request.user
        if user.is_authenticated():
            #未登录
            return  JsonResponse({'res':0,'errmsg':'用户未登录'})

        #接受参数
        addr_id = request.POST.get('addr_id')
        pay_method=request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        #校验参数
        if not all([addr_id,pay_method,sku_ids]):
            return  JsonResponse({'res':1,'errmsg':'参数不完整'})

        #校验支付方式
        if pay_method not in  OrderInfo.PAY_METHOD_CHOICES.keys():
            return JsonResponse({'res':2,'errmsg':'非法的支付方式'})

        #校验地址
        try:
            addr= Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            #地址不存在
            return JsonResponse({'res':3,'errmsg':'地址非法'})

        #todo:创建订单核心业务
            #向df_ordere_info表中添加一条记录 。缺
                # 订单order_id: 20171221_用户id 、total_count、total_price、transit_price。
        order_id =datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        #运费
        tranist_price =10
        #总数目和总金额
        total_count =0
        total_price =0

        #设置事务保存点 。可以回滚到这个位置，使得后面的撤销。
        save_id=transaction.savepoint()

        #把涉及到数据库操作的整段
        try:
            #todo:向df_ordere_info表中添加一条记录
            order =OrderInfo.objects.create(order_id=order_id,
                                            user=user,
                                            addr=addr,
                                            pay_method=pay_method,
                                            total_count=total_count,
                                            total_price=total_price,
                                            tranist_price=tranist_price)

            #用户的订单中有几个商品_就需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            sku_ids =sku_ids.split(',')   #[]

            for sku_id in sku_ids:
                for i in range(3):
                    #获取商品信息
                    try:
                        #select * from df_good_sku where id =17  for update;
                        # sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        #回滚到保存点
                        transaction.savepoint_rollback(save_id)

                        #商品不存在
                        return  JsonResponse({'res':4,'errmsg':'商品不存在'})



            #       #从redes 中获取用户所要购买的商品的数量
                    count =conn.hget(cart_key,sku_id)

                    #todo:判断商品的库存。。[因为如果有两个用户抢单，看谁先提交]
                    if int(count) > sku.stock:
                        #回滚到保存点
                        transaction.savepoint_rollback(save_id)

                        return  JsonResponse({'res':6,'errmsg':'商品库存不足'})
                    #当库存不足的时候，这个订单是下失败的，后面不应该向表里面插入信息了。


                    #todo:更新商品的库存和销量
                    orgin_stock = sku.stock
                    new_stock = orgin_stock -int(count)
                    new_sales =sku.sales + int(count)
                    #update df_goods_sku set stock=new_stock,sales = new_sales where  id= sku_id and stock = origin_stock

                    res = GoodsSKU.objects.filter(id=sku_id,stock = orgin_stock).update(stock=new_stock,
                                                                                  sales=new_sales)
                    #返回受影响的行数。。 如果返回是0，说明更新失败
                        #当有一个用户先完成，把库存给更新了，第二个用户来更新时，和原始库存不一样-==受影响的行为0，
                        #走下面逻辑：
                    if res == 0:
                        if i==2:
                            #尝试第3次
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res':7,'errmsg':'下单失败2'})
                        continue

                    #向df_order_goods中添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)


                    #todo:累加计算 订单商品的总数目和总价格
                    amount = sku.price * int(count )
                    total_count += int(count)
                    total_price += amount

                    #跳出循环
                    break

                #循环之后，更新订单信息表中的商品总数量和 总价格
                order.total_count = total_count
                order.total_price = total_price
                order.save()

        except Exception as e:  #若对数据库操作异常 -也要回滚到前面的保存点
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7,'errmsg':'下单失败'})

        #提交事务: 【前面都OK无异常之后】
        transaction.savepoint_commit(save_id)

        #清除购物车记录：用户在买完商品之后，它的购物车记录里面的商品需要删除。hdel
        conn.hdel(cart_key,*sku_ids)   #将列表 拆包，传递过去

        #返回应答
        return  JsonResponse({'res':5,'message':'创建成功'})


#ajax post
#前端传递的参数：订单id（order_id）
class OrderPayView(View):
    #订单支付
    def  post(self,request):
        #用户是否登录

        user =request.user
        if not user.is_authenticated():
            return  JsonResponse({'res':0,'errmsg':'用户未登录'})

        #接受参数
        order_id = request.POST.get('order_id')

        #校验参数
        if not  order_id:
            return JsonResponse({'res':1,'errmsg':'无效的订单id'})
            #有效的订单 : 包括 是这个用户的、支付方式、支付状态
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist: #无效订单
            return JsonResponse({'res':2,'errmsg':'订单错误'})

        #业务处理：使用python sdk调用支付宝的接口
        alipy = AliPay(
            appid='XXX',  #如果真实，使用应用的id ；沙箱环境使用沙箱的id
            app_notify_url='None',   #默认回调url。 因为网站没有ip，支付宝访问不了，None代表不传
            app_private_key_path=os.path.join(settings.BASE_DIR,'apps/order/app_private_key.pem'),
            alipy_public_key_path =os.path.join(settings.BASE_DIR,'apps/order/apliay_key.pem'),
            sign_type="RSA2",     #签名的算法
            debug= True    # True:代表 使用沙箱。否则是真实的环境
        )
            #调用支付接口
            #电脑网站支付， 需要跳转到 https://openapi.alipaydev.com/getway.do?
        total_pay = order.total_price + order.transit_price  #Decimal
        total_pay = str(total_pay)
        order_string =alipy.api_alipay_trade_app_pay(
            out_trade_no=order_id, #订单id
            total_amount= total_pay,  #支付总额
            subject='天天生鲜%s'%order_id,    #主题
            return_url =None,
            notify_url=None   # 可选，不填默认使用 notify_url
        )

        #返回应答
        pay_url = 'https://openapi.alipaydev.com/getway.do?' + order_string
        return  JsonResponse({'res':3,'pay_url':pay_url})
         #在代码里面 把用户引导到这个地址 。。。

        #内建网站，怎么知道支付结果？ 去访问支付宝接口。[实际上是 notify_url] #然后给用户显示支付结果

#ajax post
#/order/check
class CheckPayView(View):
    '''查看订单支付的结果'''
    def post(self,request):
        #查询支付结果1
        user =request.user
        if not user.is_authenticated():
            return  JsonResponse({'res':0,'errmsg':'用户未登录'})
        order_id = request.POST.get('order_id')
        if not  order_id:
            return JsonResponse({'res':1,'errmsg':'无效的订单id'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist: #无效订单
            return JsonResponse({'res':2,'errmsg':'订单错误'})
        #业务处理：使用python sdk调用支付宝的接口
        alipy = AliPay(
            appid='XXX',  #如果真实，使用应用的id ；沙箱环境使用沙箱的id
            app_notify_url='None',   #默认回调url。 因为网站没有ip，支付宝访问不了，None代表不传
            app_private_key_path=os.path.join(settings.BASE_DIR,'apps/order/app_private_key.pem'),
            alipy_public_key_path =os.path.join(settings.BASE_DIR,'apps/order/apliay_key.pem'),
            sign_type="RSA2",     #签名的算法
            debug= True    # True:代表 使用沙箱。否则是真实的环境
        )

        while True:
        #调用支付宝的交易查询 接口
            response =alipy.api_alipay_trade_query(order_id) #返回的response，查看里面的接口 字段,来判断支付结果
            code = response.get('code')
            if code =='1000' and response.get('trade_status')=='YRADE_SUCESS':
                #支付成功
                #获取支付宝交易号
                trade_no = response.get('trade_no')
                #更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  #待评价
                order.save()
                #返回应答结果
                return  JsonResponse({'res':3,'message':'支付成功'})

            elif code=='40004'or (code=='10000' and response.get('trade_status')=='WAIT_BUYER_PAY'):
                #10000等待买家付款  #40004：表示业务处理失败，可能一会就会成功
                import  time
                time.sleep(5)  #等待5秒，把查询这个地方放入一个循环。
                continue

            else:
                #支付出错
                return  JsonResponse({'res':4,'errmsg':'支付失败'})


class CommentView(LoginRequireMixin,View):
    '''订单评论    '''

    def get(self,request,order_id):
        #提供评论页面
        user= request.user
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        #根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        #获取订单商品信息
        order_skus=OrderGoods.objects.filter(order_id=order_id)
        for order_sku in  order_skus:
            #计算商品的小计
            amount=order_sku.count * order_sku.price
            #动态给order_sku 增加属性amount ,保存商品小计
            order_sku.amount = amount
        #动态给order 增加属性 order_skus ,保存订单商品信息
        order.order_status = order_sku

        #
        return render(request,"order_comment.html",{'order':order})

    def post(self,request,order_id):
        #处理评论内容
        user= request.user
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        #获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        #循环获取订单中的商品的评论内容
        for i  in range(1,total_count+1):
            #获取评论的商品的id
            sku_id = request.POST.get("sku_%d"%i) #sku_1 sku_2
            #获取评论的商品的内容
            content=request.POST.get('content_%d'%i,'')
            try:
                order_goods = OrderGoods.objects.get(order=order,sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5
        order.save()

        return redirect(reverse("user:order",kwargs={'page':1}))
        #有多少个商品就有多少个评论






















