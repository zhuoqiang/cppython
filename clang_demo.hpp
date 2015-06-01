class CppFooImpl;

class CppFoo
{
public:
    virtual void fun()
    {
        cout << "CppFoo::fun()" << endl;
    }

    virtual ~CppFoo()
    {
    }
};

inline void call_fun(CppFoo* foo)
{
    foo->fun();
}
