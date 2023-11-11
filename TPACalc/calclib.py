import geopandas as gpd 
import pandas as pd
from scipy.stats import norm
import numpy as np
import math
import matplotlib.pyplot as plt
from . import integration 

class TPACalcLib:

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
        self.tpa_paths = integration.get_tpa_paths(client_id, project_id, stand_id)
        # acres = float(self.stand_info["ACRES"])
        # if acres <= 0:
        #     raise ValueError(f"TPACalc ERROR: {client_id}, {project_id}, {stand_id} has invalid acreage")

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
        # DF: contains data for each aoi such as acreage and trees
        # metrics: contains calculated metrics about the set of aois
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

    def calculate_tpa(self, df, metrics, desired_confidence=0.95):
        # Calculate the TPA and CI for a confidence level
        tpa = metrics["total_trees"] / metrics["total_validated_acres"]
        z = norm.ppf(1 - (1 - desired_confidence) / 2)
        mean_tpa = metrics["plot_tree_average"]
        stddev = np.std(df["trees"])
        n = df.shape[0]
        ci = mean_tpa + (z * (stddev/math.sqrt(n)))
        return {"tpa": tpa, "confidence_interval": ci, "confidence_level": desired_confidence}

    def create_tpa_report(self, report):
        # Construct and write out a TPA report
        tpa = round(report['tpa'], 2)
        ci = round(report['confidence_interval'], 2)
        cl = str(int(report['confidence_level']*100)) + "%"
        report_str = f"{tpa}±{ci} @ {cl}"
        with open(self.tpa_paths['tpa_report'], 'w') as fp:
            fp.write(report_str)
        return report_str

    def plot_acreage_trees(self, df, tpa_report_str):
        # For RD, plot the acreage and tree count for a set of val AOIs
        x = list(range(df.shape[0]))
        acreage_y = df['validated_acres']
        trees_y = df['trees']
        fig, axs = plt.subplots(1, 2, figsize=(12, 6))
        axs[0].bar(x, acreage_y, color='blue')
        axs[0].set_title('Acreage')
        axs[0].set_xlabel('Index')
        axs[0].set_ylabel('Validated Acres')
        axs[1].bar(x, trees_y, color='green')
        axs[1].set_title('Trees')
        axs[1].set_xlabel('Index')
        axs[1].set_ylabel('Trees')
        axs[0].set_xticks(x)
        axs[1].set_xticks(x)
        suptitle = f"{self.client_id}-{self.project_id}-{self.stand_id}: {tpa_report_str}"
        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(self.tpa_paths['tpa_rd_plot'])
        plt.close()

    @classmethod
    def TPAReport(cls, client_id, project_id, stand_id, desired_confidence=0.95):
        self = cls(client_id, project_id, stand_id)
        df, metrics = self.inspect_aois_trees()
        report = self.calculate_tpa(df, metrics, desired_confidence)
        report_str = self.create_tpa_report(report)
        self.plot_acreage_trees(df, report_str)
        integration.set_val_tpa(client_id, project_id, stand_id, report['tpa'])

if __name__ == "__main__":
    import sys
    TPACalc.TPAReport(*sys.argv[1:4])