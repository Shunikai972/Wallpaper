"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PatchGenerator = void 0;
const utils_1 = require("../utils");
/**
 * Generates the JavaScript that is injected into workbench.html.
 *
 * The script:
 *  1. Creates a <video> element positioned as a fixed, full-screen overlay
 *  2. Applies the configured opacity, object-fit, and loop settings
 *  3. Hides the VSCode checksum-corruption notification toast
 *  4. Waits for the DOM to be ready before inserting the video
 */
class PatchGenerator {
    /**
     * Generate minified JavaScript to inject into workbench.html.
     *
     * @param config  Wallpaper configuration (with normalized video path)
     * @returns Minified JS string ready for injection into a <script> tag
     */
    static create(config) {
        const raw = PatchGenerator.buildScript(config);
        return PatchGenerator.minify(raw);
    }
    /**
     * Lightweight minifier — no external dependency needed.
     * Strips single-line comments, collapses whitespace and newlines.
     * Sufficient for the simple, self-contained script we inject.
     */
    static minify(code) {
        return (code
            // Remove single-line comments (but not URLs like https://)
            .replace(/(?<![:/])\/\/[^\n]*/g, '')
            // Collapse all whitespace sequences (spaces, tabs, newlines) to a single space
            .replace(/\s+/g, ' ')
            // Remove spaces around common operators and punctuation
            .replace(/\s*([{}();,=+\-*/<>!&|?:])\s*/g, '$1')
            .trim());
    }
    static buildScript(config) {
        const { videoPath, opacity, size, loop } = config;
        // Corruption-warning suppression (English only)
        const corruptionMessages = ['installation appears to be corrupt'];
        const suppressCSS = corruptionMessages
            .map((msg) => `.notification-toast-container:has([aria-label*="${msg}"]){display:none!important;}`)
            .join('');
        const videoScript = `
            var LW_VIDEO_ID = 'live-wallpaper-bg-video';
            var LW_STYLE_ID = 'live-wallpaper-bg-style';

            var config = {
                videoPath: ${JSON.stringify(videoPath)},
                opacity: ${opacity},
                size: ${JSON.stringify(size)},
                loop: ${loop}
            };

            function injectStyle() {
                var existing = document.getElementById(LW_STYLE_ID);
                if (existing) { existing.remove(); }

                var style = document.createElement('style');
                style.id = LW_STYLE_ID;
                style.textContent = ${JSON.stringify(suppressCSS)};
                document.head.appendChild(style);
            }

            function injectVideo() {
                // Remove any previously injected video (handles hot-reload / re-apply)
                var existing = document.getElementById(LW_VIDEO_ID);
                if (existing) { existing.remove(); }

                if (!config.videoPath) { return; }

                var video = document.createElement('video');
                video.id = LW_VIDEO_ID;
                video.src = config.videoPath;
                video.autoplay = true;
                video.loop = config.loop;
                video.muted = true;
                video.playsInline = true;

                // Suppress autoplay policy errors silently
                video.onerror = function() {};

                // Fixed full-screen overlay, behind UI but above the base background
                video.style.cssText = [
                    'position: fixed',
                    'top: 0',
                    'left: 0',
                    'width: 100vw',
                    'height: 100vh',
                    'object-fit: ' + config.size,
                    'opacity: ' + config.opacity,
                    'z-index: 999',
                    'pointer-events: none',
                    'display: block'
                ].join(';');

                document.body.appendChild(video);

                // Ensure playback starts even if the element was inserted before
                // the browser had a chance to start autoplay
                video.play().catch(function() {});
            }

            function init() {
                injectStyle();
                injectVideo();
            }

            // VSCode loads its workbench asynchronously. We wait for the body
            // to appear before injecting our overlay.
            if (document.body) {
                init();
            } else {
                document.addEventListener('DOMContentLoaded', init);
            }
        `;
        return utils_1._.withIIFE(videoScript);
    }
}
exports.PatchGenerator = PatchGenerator;
//# sourceMappingURL=PatchGenerator.js.map