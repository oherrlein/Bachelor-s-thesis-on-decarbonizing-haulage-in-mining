# Bachelor-s-thesis-on-decarbonizing-haulage-in-mining
For my Bachelor's thesis for my career of "Renewable Energy Engineering", I have chosen the topic: "Decarbonizing haulage in Open-Pit Copper mining: A technology-comparison based on the Peruvian mining sector". For the analysis, I have written a code. This code is published in this repository


About the code: All the used data is stored in yml-files. We have 4 different sets for mine-yml, with two files each. One file for the conservative scenario, on file for the progressive scenario.
For the truck-data, we also have four different sets. Each set consits of four different technologies, for which each two files exist, again for the progressive and the conservative scenario. So every truck-set includes 4*2 = 8 files.
Additionally, there is one special yml-file. This is the config.yml - file. It explains which truck set belongs to which mine.

For code execution: Use the following file structure

your repository
  -> main.py
  -> src
    -> store files config.py, loader.py, main.py, model.py, physics.py, plotting.py
  -> data
    -> store all the yml files, including config.yml

Then: execute main.py. All the necessary imports are already inlcuded in the funcions.
  
  
