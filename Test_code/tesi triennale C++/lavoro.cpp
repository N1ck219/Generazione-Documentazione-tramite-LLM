int lavoro::InserisciValoriTask(vector<int> vett, int indice)
{
    int x, y, prova = 0;

    punteggio = vett[indice];
    // cout << "p: " << punteggio << endl;
    indice++;

    num_ass_point = vett[indice];
    // cout << "nap: " << num_ass_point << endl;
    indice++;

    for (int i = 0; i < num_ass_point; i++)
    {
        x = vett[indice];
        cout << "x: " << x << endl;
        indice++;

        y = vett[indice];
        // cout << "y: " << y << endl;
        indice++;

        prova = x;
        pos.push_back(make_pair(prova, y));
        cout << pos[i].first << endl;
    }

    // cout << punteggio << " " << num_ass_point << " " << pos[0].first << " " << pos[0].second << endl;

    return indice;
}

ostream &operator<<(ostream &os, const lavoro &l)
{
    cout << "vale " << l.punteggio << " punti con " << l.num_ass_point << " punti di assemblaggio. ";

    for (int i = 0; i < l.num_ass_point; i++)
    {
        cout << "[" << l.pos[i].first << ", " << l.pos[i].second << "]";
    }

    return os;
}