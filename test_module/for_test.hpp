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
        int n = 3; // will be skipped
    }

    struct S1 {
        int a;
        CharsType b;
    };

    // typedef struct {
    //     int a;
    // } S2;

}

const long long CONST_3 = 3;

#define DEFINE_1 '1'

#endif /* _FOR_TEST_HPP_8469114_ */
