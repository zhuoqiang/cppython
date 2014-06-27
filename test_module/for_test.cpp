#include "for_test.hpp"
#include <cstring>

namespace for_test_namespace {
    
    S1 build_s1(int a, char const* b)
    {
        S1 s1 = {a, {0}};
        std::strcpy(s1.b, b);
        return s1;
    }
}
