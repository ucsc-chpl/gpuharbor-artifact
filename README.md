# Artifact for "GPUHarbor: Testing GPU Memory Consistency At Large (Experience Paper)"

## Introduction

This is the artifact for our ISSTA 2023 paper, "GPUHarbor". It contains instructions for running the tools described in the paper and includes all the data we collected as part of our GPU testing campaign. For detailed descriptions of the tools and techniques we used, please refer to the paper itself.

Figure 2 in the paper shows our overall system architecture. In this artifact we provide access to all of the tools shown there, namely litmus test generation, running tests through the web interface and Android app, and our analysis scripts. We also provide a separate Android app for reproducing the experiments described in Section 5.3. 

We walk through setting up and using all these tools in [Detailed Instructions](#detailed-instructions), but to get started, we will show how our web interface can be used to quickly explore and collect weak memory behaviors of GPUs.

## Getting Started

Our web interface is hosted at https://gpuharbor.ucsc.edu/webgpu-mem-testing. First, navigate to the page showing the [Message Passing](https://gpuharbor.ucsc.edu/webgpu-mem-testing/tests/message-passing) litmus test, which is also shown in Figure 1a of the paper. This page describes the test, shows its pseudo-code, and includes various testing stress parameters. By default, little stress is applied. To run the test, click the "Start Test" button. The results will update in realtime on the log-scale histogram. Green bars correspond to sequential behaviors (i.e. where one thread runs entirely before the other), the blue bar corresponds to interleaved behaviors (i.e. where threads interleave operations but still maintain sequential consistency), while the red bar shows the test's weak behavior. 

With the default parameters, you may see few or no weak behaviors. To increase the likelihood of seeing weak behaviors, we can apply extra stress by clicking the "Stress" preset under the "Test Parameters" panel. Try running the test again, and it is likely that you will see more weak behaviors. Note that these weak behaviors are allowed by WebGPU's memory model, so this test is used as a tuning test as described in the paper.

Ideal stress parameters for seeing weak behaviors vary depending on the GPU being tested, which is where tuning comes in. Navigate to the [Tune/Conform](https://gpuharbor.ucsc.edu/webgpu-mem-testing/tuning) page on the website. By following the instructions on this page, you will run the same experiment described in the paper, tuning over weak memory tests and running their associated conformance tests, and after it is complete you can submit your own results. This page also contains a "Tune" tab, which gives more control over tuning parameters and selecting which tests to run.



## Detailed Instructions

While the web interface is easy to use and allowed us to collect data from dozens of GPUs, it is only one part of our extensive tooling that enabled this paper, as can be seen in Figure 2 in the paper. In this section, we run through litmus test generation, collecting data using the web interface and Android app, analyzing the results, and running our lock algorithm experiments.

### Litmus Test Generation

Our Litmus Generator tool can output both WGSL and SPIR-V shaders for use in the web interface and Android app respectively. The code is hosted at https://github.com/reeselevine/litmus-generator, but this artifact also includes a Docker image with the tool already installed. To use the Docker image, first install [Docker](https://www.docker.com/get-started/). Then, load the image:

```
docker load -i gpuharbor.tar
```

And confirm it was loaded by making sure it shows up in the list of images:

```
docker images
```

Then, run the image:

```
docker run --name gpuharbor -it gpuharbor-artifact
```

Navigate to the `litmus-generator` directory. To generate the message passing shader, and its results aggregation shader, run the following commands:

For a WGSL shader:

```
python3 litmusgenerator.py --backend wgsl --gen_result_shader litmus-config/mp/message-passing.json
```

For a SPIR-V shader:

```
python3 litmusgenerator.py --backend vulkan --gen_result_shader litmus-config/mp/message-passing.json
```

The resulting shaders will be written to the `target` directory. For our paper, we then copied these shaders into the web interface/Android app source code to run them. 

### Web Interface/Android App

Using the web interface to explore/tune litmus tests was described in [Getting Started](#getting-started). However, we also include the source code for the website here, under the `webgpu-litmus` directory. The code is also hosted at https://github.com/reeselevine/webgpu-litmus. The web interface can be run locally by installing [Google Chrome Canary](https://www.google.com/chrome/canary/), following the instructions in the README to install Node.JS and NPM, and starting the app using the command `npm run dev`. This sets up a full local environment, including the server side code that collects results submitted from the frontend in a SQLite databse.

