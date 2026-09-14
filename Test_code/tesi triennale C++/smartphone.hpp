#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cmath>

#define OCC 1
#define LIB 0

using namespace std;

class lavoro
{
    friend ostream &operator<<(ostream &os, const lavoro &l);

public:
    int punteggio;
    int num_ass_point;
    vector<pair<int, int>> pos;
    // lavoro(){}; // vedere come mettere dentro le task
    void InserisciPrimi(int x, int y);
    void InserisciCoord(int x, int y);
    void svuota() { pos.clear(); };
    int getNumPos() const { return pos.size(); };
    int getCoord1(int i) const { return pos[i].first; }
    int getCoord2(int i) const { return pos[i].second; }

    lavoro &operator=(const lavoro &l);

private:
};

class griglia
{
    friend ostream &operator<<(ostream &os, const griglia &g);

private:
public:
    griglia(string nome_file);
    vector<vector<int>> valori_griglia; // indica se occupato o libero
    vector<pair<int, int>> mount_point;
    vector<lavoro> task;
    int w, h, r, m, t, l;
    int getW() const { return w; };
    int getH() const { return h; };
    int getR() const { return r; };
    int getM() const { return m; };
    int getT() const { return t; };
    int getL() const { return l; };
    vector<vector<int>> getValori() const { return valori_griglia; };
    vector<pair<int, int>> getMount_point() const { return mount_point; };
    lavoro getLavoro(int i) const { return task[i]; };
};
