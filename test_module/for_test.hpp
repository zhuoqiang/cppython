/**
   @author ZHUO Qiang
   
   @date 2014-06-23 22:55
   @file
*/

#ifndef _FOR_TEST_HPP_8469114_
#define _FOR_TEST_HPP_8469114_

namespace for_test_namespace {
    namespace inner_namespace {
    
        /////////////////////////////////////////////////////////////////////////
        /// comment for IntType
        /////////////////////////////////////////////////////////////////////////
        typedef int IntType;

        enum EnumType
        {
            ENUM_START = 0,
            ENUM_MIDDLE,
            ENUM_END = 3
        };

        int const CONST_1 = 1;
    }
    
    const unsigned long CONST_2 = 0x0A;
    typedef char CharsType[7];


    namespace bar {
        static int n = 3; // will be skipped
    }

    struct S1 {
        int a;
        CharsType b;
    };

    typedef struct {
        int a;
    } S2;

    S1 build_s1(int a, char const* b);

    void use_s1(S1& s1);
    void use_s1_pointer(S1* s1);    

    class C2
    {
    public:
        void void_method() {}
        
        C2(int a)
            : a(a)
        {}
        
        virtual int pure_virtual_method() = 0;
        
        int normal_method(int n) {
            return 1 + n + a;
        }
        
        virtual char const* char_pointer_method(int n, const char* p) {
            return p+n;
        }
        
        static int static_method() {
            return 4;
        }
        
        virtual ~C2() {}
        
        int a;
    };
    
    class C1
    {
    public:
        C1(C2* c2)
            : _c2(c2)
        {}

        virtual int virtual_method();
        virtual int virtual_method_call_other();

        virtual int on_struct(S1& s1);
        virtual int on_struct_pointer(S1* s1);
        // virtual C2* get_c2()
        // {
        //     return _c2;
        // }

        virtual ~C1();
        
    private:
        C2* _c2;
    };

    inline int call_c1_virtual_method(C1* c1)
    {
        return c1->virtual_method();
    }
    
    inline const char* call_c1_char_method(C2* o, int n, char const* p)
    {
        return o->char_pointer_method(n, p);
    }
    
    inline void void_fun()
    {
    }
}

const long long CONST_3 = 3;

#define DEFINE_1 '1'

#endif /* _FOR_TEST_HPP_8469114_ */
