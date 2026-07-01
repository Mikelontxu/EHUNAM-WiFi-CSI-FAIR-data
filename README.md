# EHUNAM-WiFi-CSI-FAIR-data

Process of transforming the WiFi CSI-based dataset for human recognition and machine detection made by EHUNAM to a FAIR dataset.

The original dataset contains raw `.mat` files without FAIR metadata. 
This project transforms those files into RDF/OWL following FAIR principles.

**Project status**: this project is currently under development and being tested at **http://34.51.146.173**

## Content

* [Structure](#structure)
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
<p>This folder contains the EHUNAM WiFi CSI Activity Ontology (wifi_activity.ttl) and its documentation. This includes defining the classes, object properties, and data properties used to  describe each WiFi measurement (e.g. activity, environment, application, WiFi standard, CSI extractor, etc.).</p>  
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
</tbody>  
</table>

## User manual

1. Install all the requirements:
```bash
   pip install -r requirements.txt
```

2. Build the FDP Docker environment (see the `/fdp` folder's README for more details):
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
