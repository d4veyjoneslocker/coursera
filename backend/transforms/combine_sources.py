import pandas as pd
import numpy as np

def combine_distributors(unfi, kehe):

    # combining unfi and kehe dataframes
    combined = pd.concat([unfi, kehe], ignore_index=True)

    # return combined table

    return combined