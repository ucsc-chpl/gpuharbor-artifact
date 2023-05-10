# Artifact for "GPUHarbor: Testing GPU Memory Consistency At Large (Experience Paper)"

## Introduction

This is the artifact for our ISSTA 2023 paper, "GPUHarbor". It contains instructions for running the tools described in the paper and includes all the data we collected as part of our GPU testing campaign. For detailed descriptions of the tools and techniques we used, please refer to the paper itself.

Figure 2 in the paper shows our overall system architecture. In this artifact we provide access to all of the tools shown there, namely litmus test generation, running tests through the web interface and Android app, and our analysis scripts. We also provide a separate Android app for reproducing the experiments described in Section 5.3. 

We walk through setting up and using all these tools in [Detailed Instructions](#detailed-instructions), but to get started, we will show how our web interface can be used to quickly explore and collect weak memory behaviors of GPUs.

## Getting Started

Our web interface is hosted at https://gpuharbor.ucsc.edu/webgpu-mem-testing. First, navigate to the page showing the [Message Passing](https://gpuharbor.ucsc.edu/webgpu-mem-testing/tests/message-passing) litmus test, which is also shown in Figure 1a of the paper. This page describes the test, shows its pseudo-code, and includes various testing stress parameters. By default, no major stress is applied. To run the test, click the "Start Test" button. The results will update in realtime in the histogram. Green bars correspond to sequential behaviors (i.e. where one thread runs entirely before the other), the blue bar corresponds to interleaved behaviors (i.e. where threads interleave operations but still maintain sequential consistency), while the red bar shows the test's weak behavior. 


## Detailed Instructions


