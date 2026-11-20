/**
 * iOS 27 refuses to launch apps that haven't adopted the scene-based life cycle
 * (UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption). Expo 57.0.33 ships
 * `ExpoAppSceneDelegate`, but only the SDK 58 app template wires it in. This applies SDK 58's
 * exact setup to SDK 57 projects. Remove it when upgrading to SDK 58, whose template has it.
 */
const fs = require("fs");
const path = require("path");
const {
  IOSConfig,
  withAppDelegate,
  withDangerousMod,
  withInfoPlist,
  withXcodeProject,
} = require("expo/config-plugins");

const SCENE_DELEGATE = `internal import Expo

@objc(SceneDelegate)
class SceneDelegate: ExpoAppSceneDelegate {
  // Extension point for config plugins.
}
`;

function withSceneManifest(config) {
  return withInfoPlist(config, (plist) => {
    plist.modResults.UIApplicationSceneManifest = {
      UIApplicationSupportsMultipleScenes: false,
      UISceneConfigurations: {
        UIWindowSceneSessionRoleApplication: [
          {
            UISceneConfigurationName: "Default Configuration",
            UISceneDelegateClassName: "$(PRODUCT_MODULE_NAME).SceneDelegate",
          },
        ],
      },
    };
    return plist;
  });
}

function withSceneAppDelegate(config) {
  return withAppDelegate(config, (delegate) => {
    let source = delegate.modResults.contents;
    if (source.includes("ExpoReactNativeFactoryProvider")) return delegate;
    const declaration = /class AppDelegate: ExpoAppDelegate \{/;
    const windowStart = /\n#if os\(iOS\) \|\| os\(tvOS\)\n\s*window = UIWindow[\s\S]*?#endif\n/;
    if (!declaration.test(source) || !windowStart.test(source)) {
      throw new Error(
        "with-ios-scene-lifecycle: AppDelegate.swift no longer matches the SDK 57 template. " +
          "If this is SDK 58 or later, remove this plugin.",
      );
    }
    source = source
      .replace(declaration, "class AppDelegate: ExpoAppDelegate, ExpoReactNativeFactoryProvider {")
      // SceneDelegate creates the window and starts React Native under the scene life cycle.
      .replace(windowStart, "\n");
    delegate.modResults.contents = source;
    return delegate;
  });
}

function withSceneDelegateFile(config) {
  config = withDangerousMod(config, [
    "ios",
    (modConfig) => {
      const target = path.join(
        modConfig.modRequest.platformProjectRoot,
        modConfig.modRequest.projectName,
        "SceneDelegate.swift",
      );
      fs.writeFileSync(target, SCENE_DELEGATE);
      return modConfig;
    },
  ]);
  return withXcodeProject(config, (xcode) => {
    const name = xcode.modRequest.projectName;
    const filepath = `${name}/SceneDelegate.swift`;
    if (!xcode.modResults.hasFile(filepath)) {
      IOSConfig.XcodeUtils.addBuildSourceFileToGroup({
        filepath,
        groupName: name,
        project: xcode.modResults,
      });
    }
    return xcode;
  });
}

module.exports = function withIosSceneLifecycle(config) {
  return withSceneDelegateFile(withSceneAppDelegate(withSceneManifest(config)));
};
