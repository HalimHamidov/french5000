package com.french5000.vocab;

import android.os.Bundle;
import androidx.core.view.WindowCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Draw edge-to-edge so CSS safe-area-inset-* are populated correctly
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
    }
}
