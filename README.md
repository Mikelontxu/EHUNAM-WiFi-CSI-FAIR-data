# EHUNAM-WiFi-CSI-FAIR-data

Process of transforming the WiFi CSI-based dataset for human recognition and machine detection made by EHUNAM to a FAIR dataset.

The original dataset contains raw `.mat` files without FAIR metadata. 
This project transforms those files into RDF/OWL following FAIR principles.

**Project status**: this project is currently under development and being tested at **http://34.51.146.173**

## Content

* [Structure](#structure)
* [Prerequisites](#prerequisites)
* [User manual](#user-manual)
* [License](#license)
* [Disclaimer](#disclaimer)

## Structure

<table>  
<tbody>  
<tr>  
<td>  
<p><strong>Folder</strong></p>  
</td>  
<td>  
<p><strong>Description</strong></p>  
</td>  
</tr>  
<tr>  
<td>  
<p>/data:</p>  
</td> 
<td>  
<p>This folder stores all the raw <code>.mat</code> files containing the WiFi CSI/RSSI measurements and timestamps obtained during the data collection of the original dataset.</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/fdp:</p>  
</td> 
<td>  
<p>This folder contains the Docker environment that deploys and runs the FAIR Data Point (FDP) along with the other  services required to publish the dataset following FAIR principles (GraphDB, mongodb, nginx, widoco and FUJI).</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/ontology:</p>  
</td> 
<td>  
<p>This folder contains the EHUNAM WiFi CSI Activity Ontology (wifi_activity.ttl).This includes defining the classes, object properties, and data properties used to  describe each WiFi measurement (e.g. activity, environment, application, WiFi standard, CSI extractor, etc.).</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/docs:</p>  
</td> 
<td>  
<p>This folder contains the EHUNAM WiFi CSI Activity Ontology documentation. This includes differente formats for the ontology and a human readable documentation.</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/scripts:</p>  
</td> 
<td>  
<p>This folder contains the scripts that parse and process the <code>.mat</code> files, convert their metadata into RDF instances based on the ontology, and upload the resulting triples to GraphDB, organizing them into uniquely named graphs per measurement.</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/shapes:</p>  
</td> 
<td>  
<p>This folder contains the SHACL shapes used to validate the RDF data generated against the ontology. It also includes the standard DCAT-AP SHACL shapes used to evaluate and validate the dataset metadata.</p>  
</td>  
</tr> 
<tr>  
<td>  
<p>/test:</p>  
</td> 
<td>  
<p>This folder contains some tests to validate the use of the SPARQL endpoint and prove that it works properly. Use <code> python test/test_sparql_endpoint.py </code> to execute the script and download the proper .mat files. The SPARQL queries can be changed for further testing.</p>  
</td>  
</tr> 
</tbody>  
</table>

## Prerequisites

- A /data folder with .mat files of EHUNAM dataset.
- A system with at least (2 vCPUs, 4 GB RAM memory).
- Enough storage space for the EHUNAM dataset (recommended at least 70GB for MC1).

## User manual

**Before Deployment:**
- Change the shapes and fdp files to match the correct IP/URI.

1. Install all the requirements:
```bash
   pip install -r requirements.txt
```

2. Build the FDP Docker environment (**see the `/fdp` folder's README for more details**):
```bash
   docker compose up -d
```

3. Run the pipeline:
```bash
   python scripts/pipeline.py
```

4. The resulting RDF data should now be loaded into your GraphDB instance.

## License

- **Ontology, scripts, original dataset and code in this repository**: licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Disclaimer

As mentioned previously, all the data is property of EHUNAM. The original dataset and article are open and can be accessed using their DOIs.

**Original dataset**: [EHUNAM WiFi CSI Dataset on Figshare](https://doi.org/10.6084/m9.figshare.28541225)

**Original article**: [EHUNAM, a WiFi CSI-based dataset for human and machine sensing](https://doi.org/10.1038/s41597-025-06238-4)
