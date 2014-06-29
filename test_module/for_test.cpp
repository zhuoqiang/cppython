#include "for_test.hpp"
#include <cstring>
#include <iostream>

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

    int C1::f()
    {
        return 1 + _c2->get();
    }
}
