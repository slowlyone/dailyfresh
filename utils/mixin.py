from  django.contrib.auth.decorators import login_required

class LoginRequireMixin(object):#定义一个类方法
    @classmethod
    def as_view(cls,**initkwargs):  #as_view()方法的参数和 View里面的as_view()方法一致

        view=super(LoginRequireMixin,cls).as_view(**initkwargs) #调用父类的as_view，得到返回值赋给view
        return login_required(view)  #使用login_required()对view对它进行包装
