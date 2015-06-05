#include "for_test.hpp"
#include <cstring>
#include <iostream>

using namespace std;

namespace for_test_namespace {
    
    S1 build_s1(int a, char const* b)
    {
        S1 s1 = {a};
        std::strcpy(s1.b, b);
        return s1;
    }

    void use_s1(S1& s1)
    {
        std::cout << s1.a << s1.b << std::endl;
        s1.a = 1024;
    }

    void use_s1_pointer(S1* s1)
    {
        s1->a = 777;        
    }
    
    int C1::virtual_method()
    {
        return 1;
    }

    int C1::virtual_method_call_other()
    {
        return 1 + _c2->pure_virtual_method();
    }

    int C1::on_struct(S1& s1)
    {
        int old = s1.a;
        s1.a = 111;
        return old;
    }

    int C1::on_struct_pointer(S1* s1)
    {
        int old = s1->a;
        s1->a = 222;
        return old;
    }
    
    C1::~C1()
    {
        _c2->a = 1024;
        cout << "\nC1::~C1()" << endl;
    }
    
}
