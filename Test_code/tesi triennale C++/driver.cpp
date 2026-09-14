#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cmath>
#include "smartphone.hpp"
#include "istruzioni.hpp"

#define OCC 1
#define LIB 0

using namespace std;

int main()
{
    char c;
    string nome_file;

    cout << "Scegli file da usare (a,b,c,d,e,f): ";
    cin >> c;

    if (c == 'a')
    {
        nome_file = "input/a_example.txt";
    }
    else if (c == 'b')
    {
        nome_file = "input/b_single_arm.txt";
    }
    else if (c == 'c')
    {
        nome_file = "input/c_few_arms.txt";
    }
    else if (c == 'd')
    {
        nome_file = "input/d_tight_schedule.txt";
    }
    else if (c == 'e')
    {
        nome_file = "input/e_dense_workspace.txt";
    }
    else if (c == 'f')
    {
        nome_file = "input/f_decentralized.txt";
    }
    else
    {
        cout << "Nessun file trovato" << endl;
        return 0;
    }

    griglia g(nome_file);
    cout << g;

    istruzioni i(g);

    cout << i;

    // for (int j = (g.h - 1); j >= 0; j--)
    // {

    //     for (int i = 0; i < g.w; i++)
    //     {
    //         // cout << "w: " << i << " h: " << j << " " << g.valori_griglia[i][j] << endl;
    //         cout << g.valori_griglia[i][j];
    //     }
    //     cout << " " << j;
    //     cout << endl;
    // }
    // // cout << " 01234" << endl;
    return 0;
}