driver: smartphone.o driver.o istruzioni.o
	g++ -o driver smartphone.o driver.o istruzioni.o

smartphone.o: smartphone.cpp smartphone.hpp
	g++ -c -Wall -Wfatal-errors smartphone.cpp

driver.o: driver.cpp smartphone.hpp
	g++ -c -Wall -Wfatal-errors driver.cpp

istruzioni.o: istruzioni.cpp istruzioni.hpp smartphone.hpp
	g++ -c -Wall -Wfatal-errors istruzioni.cpp

clean:
	rm -f driver smartphone.o driver.o istruzioni.o

