import geopandas as gpd 
import pandas as pd
from scipy.stats import norm
import numpy as np
import math
import integration 

class TPACalc:

    def __init__(self, client_id, project_id, stand_id):
        ''' 
        Constuct a TPACalc instance given IDs for a client, project, and stand
        Requires that the number of aois and trees exist, and acreage is valid in the DB
        '''
        self.client_id = client_id
        self.project_id = project_id
        self.stand_id = stand_id
        req = integration.get_val_paths(client_id, project_id, stand_id)
        self.aois = req["filepath"]["aoi"]
        self.trees = req["filepath"]["points"]
        if not len(self.aois) == len(self.trees):
            raise ValueError(f"TPACalc ERROR: {client_id}, {project_id}, {stand_id} has mismatched number of AOIS and trees")
        self.stand_info = integration.get_stand_info(client_id, project_id, stand_id)
        acres = self.stand_info["ACRES"] 
        if acres <= 0:
            raise ValueError(f"TPACalc ERROR: {client_id}, {project_id}, {stand_id} has invalid acreage")

    def _calc_aoi_acreage(self, i):
        # Calculate the acreage of aoi_i
        aoi = self.aois[i]
        gdf = gpd.read_file(aoi, driver="GeoJSON")
        gdf = gdf.to_crs("EPSG:32610")
        gdf['area_m2'] = gdf['geometry'].area
        gdf['area_acres'] = gdf['area_m2'] / 4046.85642
        return gdf['area_acres'][0]

    def _count_trees(self, i):
        # Count the trees in Buffered_Trees_i
        trees = self.trees[i]
        gdf = gpd.read_file(trees, driver="GeoJSON")
        return gdf.shape[0]

    def inspect_aois_trees(self):
        # Analyze and record metrics on the labeled validation data
        df = {"validated_acres": [], "trees": []}
        for i in range(len(self.aois)):
            df["validated_acres"].append(self._calc_aoi_acreage(i))
            df["trees"].append(self._count_trees(i))
        df = pd.DataFrame(df)
        metrics = {
            "total_validated_acres": df["validated_acres"].sum(),
            "total_trees": df["trees"].sum(),
            "plot_tree_average": df["trees"].mean()
        }
        return df, metrics

    def calculate_tpa(self, df, metrics, desired_confidence=0.99):
        # Calculate the TPA and CI for a confidence level
        tpa = metrics["total_trees"] / metrics["total_validated_acres"]
        z = norm.ppf(1 - (1 - desired_confidence) / 2)
        mean_tpa = metrics["plot_tree_average"]
        stddev = np.std(df["trees"])
        n = df.shape[0]
        ci = mean_tpa + (z * (stddev/math.sqrt(n)))
        return {"tpa": tpa, "confidence_interval": ci}

    @classmethod
    def TPAReport(cls, client_id, project_id, stand_id, desired_confidence=0.99):
        self = cls(client_id, project_id, stand_id)
        df, metrics = self.inspect_aois_trees()
        report = self.calculate_tpa(df, metrics, desired_confidence)
        integration.set_val_tpa(report["tpa"])

if __name__ == "__main__":
    import sys
    TPACalc.TPAReport(*sys.argv[1:4])