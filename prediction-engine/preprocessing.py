import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer, KNNImputer
import logging

logger = logging.getLogger(__name__)

class FeaturePreprocessor:
    """Feature preprocessing for ML models"""
    
    def __init__(self):
        self.numerical_columns = []
        self.categorical_columns = []
        self.text_columns = []
        self.datetime_columns = []
        
        self.scaler = None
        self.encoder = None
        self.imputer = None
        self.label_encoders = {}
        self.feature_names = []
        
    def fit(self, df: pd.DataFrame) -> 'FeaturePreprocessor':
        """Fit the preprocessor to the data"""
        self._identify_column_types(df)
        self._create_preprocessing_pipeline()
        return self
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform the data using fitted preprocessor"""
        if not self.scaler or not self.encoder:
            raise ValueError("Preprocessor not fitted. Call fit() first.")
        
        # Make a copy to avoid modifying original
        df_transformed = df.copy()
        
        # Handle missing values
        if self.imputer:
            df_transformed = self._handle_missing_values(df_transformed)
        
        # Transform numerical columns
        if self.numerical_columns:
            df_transformed[self.numerical_columns] = self.scaler.transform(
                df_transformed[self.numerical_columns]
            )
        
        # Transform categorical columns
        if self.categorical_columns:
            encoded_data = self.encoder.transform(df_transformed[self.categorical_columns])
            encoded_df = pd.DataFrame(
                encoded_data,
                columns=self.encoder.get_feature_names_out(self.categorical_columns),
                index=df_transformed.index
            )
            
            # Drop original categorical columns and add encoded ones
            df_transformed = df_transformed.drop(columns=self.categorical_columns)
            df_transformed = pd.concat([df_transformed, encoded_df], axis=1)
        
        # Handle text columns (if any)
        if self.text_columns:
            df_transformed = self._process_text_features(df_transformed)
        
        # Handle datetime columns
        if self.datetime_columns:
            df_transformed = self._process_datetime_features(df_transformed)
        
        # Store feature names
        self.feature_names = df_transformed.columns.tolist()
        
        return df_transformed
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step"""
        return self.fit(df).transform(df)
    
    def get_feature_names(self) -> List[str]:
        """Get the names of transformed features"""
        return self.feature_names
    
    def _identify_column_types(self, df: pd.DataFrame):
        """Identify different types of columns"""
        for column in df.columns:
            dtype = df[column].dtype
            
            if pd.api.types.is_numeric_dtype(dtype):
                self.numerical_columns.append(column)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                self.datetime_columns.append(column)
            elif dtype == 'object':
                # Check if it's categorical or text
                unique_ratio = df[column].nunique() / len(df)
                if unique_ratio < 0.5 or df[column].nunique() < 20:
                    self.categorical_columns.append(column)
                else:
                    self.text_columns.append(column)
            else:
                # Default to categorical
                self.categorical_columns.append(column)
        
        logger.info(f"Identified {len(self.numerical_columns)} numerical, "
                   f"{len(self.categorical_columns)} categorical, "
                   f"{len(self.text_columns)} text, "
                   f"{len(self.datetime_columns)} datetime columns")
    
    def _create_preprocessing_pipeline(self):
        """Create preprocessing pipeline"""
        # Numerical preprocessing
        if self.numerical_columns:
            self.scaler = RobustScaler()  # More robust to outliers
            self.imputer = KNNImputer(n_neighbors=5)  # Better than mean/median
        
        # Categorical preprocessing
        if self.categorical_columns:
            self.encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values"""
        if self.imputer:
            # Impute numerical columns
            if self.numerical_columns:
                df[self.numerical_columns] = self.imputer.fit_transform(
                    df[self.numerical_columns]
                )
            
            # Impute categorical columns with mode
            if self.categorical_columns:
                for col in self.categorical_columns:
                    mode_value = df[col].mode()[0] if not df[col].mode().empty else 'unknown'
                    df[col] = df[col].fillna(mode_value)
        
        return df
    
    def _process_text_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process text features"""
        for col in self.text_columns:
            if col in df.columns:
                # Simple text processing for now
                df[f'{col}_length'] = df[col].astype(str).str.len()
                df[f'{col}_word_count'] = df[col].astype(str).str.split().str.len()
                
                # Drop original text column
                df = df.drop(columns=[col])
        
        return df
    
    def _process_datetime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process datetime features"""
        for col in self.datetime_columns:
            if col in df.columns:
                # Extract datetime components
                df[f'{col}_year'] = df[col].dt.year
                df[f'{col}_month'] = df[col].dt.month
                df[f'{col}_day'] = df[col].dt.day
                df[f'{col}_weekday'] = df[col].dt.weekday
                df[f'{col}_hour'] = df[col].dt.hour
                df[f'{col}_quarter'] = df[col].dt.quarter
                
                # Drop original datetime column
                df = df.drop(columns=[col])
        
        return df
    
    def create_feature_importance_mapping(self) -> Dict[str, str]:
        """Create mapping from original to transformed feature names"""
        mapping = {}
        
        # Numerical features remain the same
        for col in self.numerical_columns:
            mapping[col] = col
        
        # Categorical features get encoded
        if self.categorical_columns and self.encoder:
            encoded_names = self.encoder.get_feature_names_out(self.categorical_columns)
            for original_col in self.categorical_columns:
                for encoded_name in encoded_names:
                    if encoded_name.startswith(f"{original_col}_"):
                        mapping[encoded_name] = original_col
        
        # Text and datetime features get transformed
        for col in self.text_columns:
            mapping[f'{col}_length'] = col
            mapping[f'{col}_word_count'] = col
        
        for col in self.datetime_columns:
            for suffix in ['_year', '_month', '_day', '_weekday', '_hour', '_quarter']:
                mapping[col + suffix] = col
        
        return mapping
    
    def save(self, filepath: str):
        """Save the preprocessor"""
        import joblib
        
        preprocessor_data = {
            'numerical_columns': self.numerical_columns,
            'categorical_columns': self.categorical_columns,
            'text_columns': self.text_columns,
            'datetime_columns': self.datetime_columns,
            'scaler': self.scaler,
            'encoder': self.encoder,
            'imputer': self.imputer,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names
        }
        
        joblib.dump(preprocessor_data, filepath)
        logger.info(f"Preprocessor saved to {filepath}")
    
    def load(self, filepath: str):
        """Load the preprocessor"""
        import joblib
        
        preprocessor_data = joblib.load(filepath)
        
        self.numerical_columns = preprocessor_data['numerical_columns']
        self.categorical_columns = preprocessor_data['categorical_columns']
        self.text_columns = preprocessor_data['text_columns']
        self.datetime_columns = preprocessor_data['datetime_columns']
        self.scaler = preprocessor_data['scaler']
        self.encoder = preprocessor_data['encoder']
        self.imputer = preprocessor_data['imputer']
        self.label_encoders = preprocessor_data['label_encoders']
        self.feature_names = preprocessor_data['feature_names']
        
        logger.info(f"Preprocessor loaded from {filepath}")

class FeatureSelector:
    """Feature selection for ML models"""
    
    def __init__(self, method: str = 'correlation', threshold: float = 0.95):
        self.method = method
        self.threshold = threshold
        self.selected_features = []
        self.feature_importance = {}
    
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'FeatureSelector':
        """Fit the feature selector"""
        if self.method == 'correlation':
            self._correlation_selection(X)
        elif self.method == 'variance':
            self._variance_selection(X)
        elif self.method == 'mutual_info' and y is not None:
            self._mutual_info_selection(X, y)
        elif self.method == 'importance' and y is not None:
            self._importance_selection(X, y)
        
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform the data by selecting features"""
        if not self.selected_features:
            raise ValueError("Feature selector not fitted. Call fit() first.")
        
        return X[self.selected_features]
    
    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit and transform in one step"""
        return self.fit(X, y).transform(X)
    
    def get_selected_features(self) -> List[str]:
        """Get the selected feature names"""
        return self.selected_features
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return self.feature_importance
    
    def _correlation_selection(self, X: pd.DataFrame):
        """Select features based on correlation"""
        # Calculate correlation matrix
        corr_matrix = X.corr().abs()
        
        # Find highly correlated features
        upper_tri = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        
        # Select features to remove
        to_remove = [column for column in upper_tri.columns 
                    if any(upper_tri[column] > self.threshold)]
        
        # Keep features that are not highly correlated
        self.selected_features = [col for col in X.columns if col not in to_remove]
        
        logger.info(f"Correlation selection: removed {len(to_remove)} features, "
                   f"kept {len(self.selected_features)} features")
    
    def _variance_selection(self, X: pd.DataFrame):
        """Select features based on variance"""
        from sklearn.feature_selection import VarianceThreshold
        
        selector = VarianceThreshold(threshold=0.01)  # Remove low variance features
        selector.fit(X)
        
        self.selected_features = X.columns[selector.get_support()].tolist()
        
        logger.info(f"Variance selection: kept {len(self.selected_features)} features")
    
    def _mutual_info_selection(self, X: pd.DataFrame, y: pd.Series):
        """Select features based on mutual information"""
        from sklearn.feature_selection import mutual_info_classif
        
        # Calculate mutual information
        mi_scores = mutual_info_classif(X, y)
        
        # Create feature importance mapping
        self.feature_importance = dict(zip(X.columns, mi_scores))
        
        # Select top features (keep top 80% or features with MI > 0.01)
        threshold = np.percentile(mi_scores, 20)  # Keep top 80%
        self.selected_features = [
            col for col, score in self.feature_importance.items() 
            if score >= max(threshold, 0.01)
        ]
        
        logger.info(f"Mutual information selection: kept {len(self.selected_features)} features")
    
    def _importance_selection(self, X: pd.DataFrame, y: pd.Series):
        """Select features based on model importance"""
        from sklearn.ensemble import RandomForestClassifier
        
        # Train a simple Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # Get feature importance
        importance_scores = rf.feature_importances_
        self.feature_importance = dict(zip(X.columns, importance_scores))
        
        # Select features with importance > threshold
        self.selected_features = [
            col for col, score in self.feature_importance.items() 
            if score >= self.threshold
        ]
        
        logger.info(f"Importance selection: kept {len(self.selected_features)} features")
